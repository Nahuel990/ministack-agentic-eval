"""Assertions for s3_logs_bucket. Each returns (passed, expected, observed)."""
from botocore.exceptions import ClientError

BUCKET = "app-logs-001"
PAB_FLAGS = ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")


def _error_code(e: ClientError) -> str:
    return e.response.get("Error", {}).get("Code", "unknown")


def bucket_exists(ctx):
    try:
        ctx.client("s3").head_bucket(Bucket=BUCKET)
        return True, f"bucket {BUCKET} exists", "HeadBucket succeeded"
    except ClientError as e:
        return False, f"bucket {BUCKET} exists", f"HeadBucket failed: {_error_code(e)}"


def versioning_not_enabled(ctx):
    # Real AWS has exactly three states: never set (no Status), Enabled, Suspended.
    # MiniStack also stores invalid values (e.g. "Disabled") that AWS would reject,
    # so only the two valid "off" states pass.
    expected = "versioning never set or Suspended"
    try:
        status = ctx.client("s3").get_bucket_versioning(Bucket=BUCKET).get("Status")
    except ClientError as e:
        return False, expected, f"GetBucketVersioning failed: {_error_code(e)}"
    if status not in (None, "Enabled", "Suspended"):
        return False, expected, f"Status={status}, not a valid AWS versioning state (real AWS rejects PutBucketVersioning with it)"
    return status != "Enabled", expected, f"Status={status or '<never set>'}"


def public_access_fully_blocked(ctx):
    expected = "all four PublicAccessBlock flags true"
    try:
        cfg = ctx.client("s3").get_public_access_block(Bucket=BUCKET)["PublicAccessBlockConfiguration"]
    except ClientError as e:
        return False, expected, f"GetPublicAccessBlock failed: {_error_code(e)}"
    not_true = [f for f in PAB_FLAGS if cfg.get(f) is not True]
    observed = ", ".join(f"{f}={cfg.get(f)}" for f in PAB_FLAGS)
    if not_true:
        observed += f" (not true: {', '.join(not_true)})"
    return not not_true, expected, observed


def lifecycle_expires_30_days(ctx):
    expected = "a rule with Status=Enabled and Expiration.Days=30"
    try:
        rules = ctx.client("s3").get_bucket_lifecycle_configuration(Bucket=BUCKET).get("Rules", [])
    except ClientError as e:
        return False, expected, f"GetBucketLifecycleConfiguration failed: {_error_code(e)}"
    ok = any(r.get("Status") == "Enabled" and r.get("Expiration", {}).get("Days") == 30 for r in rules)
    seen = [f"{{ID={r.get('ID')}, Status={r.get('Status')}, Expiration={r.get('Expiration')}}}" for r in rules]
    return ok, expected, f"{len(rules)} rule(s): {'; '.join(seen) or 'none'}"


ASSERTIONS = {
    "bucket_exists": bucket_exists,
    "versioning_not_enabled": versioning_not_enabled,
    "public_access_fully_blocked": public_access_fully_blocked,
    "lifecycle_expires_30_days": lifecycle_expires_30_days,
}
