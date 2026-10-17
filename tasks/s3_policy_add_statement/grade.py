"""Assertions for s3_policy_add_statement. Each returns (passed, expected, observed)."""
from botocore.exceptions import ClientError

from grader.policy import PolicyError, action_matches, as_list, describe, equivalent, parse_policy, principals, resource_matches, statements

BUCKET = "reports-001"
BUCKET_ARN = f"arn:aws:s3:::{BUCKET}"
REQUIRED_RESOURCES = (BUCKET_ARN, f"{BUCKET_ARN}/*")


def _policy(ctx):
    try:
        raw = ctx.client("s3").get_bucket_policy(Bucket=BUCKET)["Policy"]
    except ClientError as e:
        return None, f"GetBucketPolicy failed: {e.response['Error'].get('Code')}"
    try:
        return parse_policy(raw), None
    except PolicyError as e:
        return None, str(e)


def policy_valid_for_bucket(ctx):
    expected = f"valid JSON policy whose Resources are all {BUCKET_ARN} or {BUCKET_ARN}/..."
    policy, err = _policy(ctx)
    if err:
        return False, expected, err
    bad = [r for s in statements(policy) for r in as_list(s.get("Resource")) + as_list(s.get("NotResource"))
           if not (r == BUCKET_ARN or r.startswith(BUCKET_ARN + "/"))]
    return not bad, expected, f"foreign/invalid resources: {bad}" if bad else f"{len(statements(policy))} statement(s), resources OK"


def analytics_read_preserved(ctx):
    seeded = ctx.seed["policy"]["Statement"][0]
    expected = f"statement equivalent to {describe(seeded)}"
    policy, err = _policy(ctx)
    if err:
        return False, expected, err
    ok = any(equivalent(s, seeded) for s in statements(policy))
    return ok, expected, "present" if ok else f"not found; statements: {[describe(s) for s in statements(policy)]}"


def _is_https_deny(s, resource):
    cond = {op.lower(): {k.lower(): [str(v).lower() for v in as_list(vals)] for k, vals in kv.items()}
            for op, kv in (s.get("Condition") or {}).items()}
    return (
        s.get("Effect") == "Deny"
        and ("*", "*") in principals(s)
        and any(a.lower() in ("s3:*", "*") for a in as_list(s.get("Action")))
        and any(resource_matches(r, resource) for r in as_list(s.get("Resource")))
        and cond == {"bool": {"aws:securetransport": ["false"]}}
    )


def deny_insecure_transport(ctx):
    expected = f"Deny * s3:* if Bool aws:SecureTransport=false, covering {list(REQUIRED_RESOURCES)}"
    policy, err = _policy(ctx)
    if err:
        return False, expected, err
    stmts = statements(policy)
    uncovered = [r for r in REQUIRED_RESOURCES if not any(_is_https_deny(s, r) for s in stmts)]
    denies = [describe(s) for s in stmts if s.get("Effect") == "Deny"]
    observed = "covered" if not uncovered else f"not covered: {uncovered}; Deny statements: {denies or 'none'}"
    return not uncovered, expected, observed


ASSERTIONS = {
    "policy_valid_for_bucket": policy_valid_for_bucket,
    "analytics_read_preserved": analytics_read_preserved,
    "deny_insecure_transport": deny_insecure_transport,
}
