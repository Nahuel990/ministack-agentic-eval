"""Assertions for s3_lifecycle_add_rule. Each returns (passed, expected, observed)."""
import json

from botocore.exceptions import ClientError

BUCKET = "app-data-001"


def _rules(ctx):
    try:
        return ctx.client("s3").get_bucket_lifecycle_configuration(Bucket=BUCKET).get("Rules", []), None
    except ClientError as e:
        return None, f"GetBucketLifecycleConfiguration failed: {e.response['Error'].get('Code')}"


def _fmt(rule) -> str:
    return json.dumps(rule, sort_keys=True, default=str)


def rule_count_is_3(ctx):
    rules, err = _rules(ctx)
    if err:
        return False, "3 rules", err
    return len(rules) == 3, "3 rules", f"{len(rules)} rule(s): {[r.get('ID') for r in rules]}"


def _unchanged(ctx, rule_id):
    seeded = next(r for r in ctx.seed["rules"] if r["ID"] == rule_id)
    expected = f"rule {_fmt(seeded)}"
    rules, err = _rules(ctx)
    if err:
        return False, expected, err
    current = [r for r in rules if r.get("ID") == rule_id]
    if not current:
        return False, expected, f"rule {rule_id} is gone; remaining IDs: {[r.get('ID') for r in rules]}"
    if len(current) > 1:
        return False, expected, f"{len(current)} rules with ID {rule_id}"
    return current[0] == seeded, expected, f"rule {_fmt(current[0])}"


def archive_logs_unchanged(ctx):
    return _unchanged(ctx, "archive-logs")


def expire_cache_unchanged(ctx):
    return _unchanged(ctx, "expire-cache")


def _prefix(rule):
    """Prefix the rule is scoped to, or None if it also filters on tags/size."""
    f = rule.get("Filter")
    if f is None:
        return rule.get("Prefix")
    if set(f) <= {"Prefix"}:
        return f.get("Prefix", "")
    if set(f) == {"And"} and set(f["And"]) == {"Prefix"}:
        return f["And"]["Prefix"]
    return None


def tmp_rule_expires_after_7_days(ctx):
    expected = "new rule: Status=Enabled, prefix tmp/, Expiration.Days=7"
    rules, err = _rules(ctx)
    if err:
        return False, expected, err
    seeded_ids = {r["ID"] for r in ctx.seed["rules"]}
    new = [r for r in rules if r.get("ID") not in seeded_ids]
    ok = any(
        r.get("Status") == "Enabled" and _prefix(r) == "tmp/" and r.get("Expiration", {}).get("Days") == 7
        for r in new
    )
    return ok, expected, f"new rule(s): {[_fmt(r) for r in new] or 'none'}"


ASSERTIONS = {
    "rule_count_is_3": rule_count_is_3,
    "archive_logs_unchanged": archive_logs_unchanged,
    "expire_cache_unchanged": expire_cache_unchanged,
    "tmp_rule_expires_after_7_days": tmp_rule_expires_after_7_days,
}
