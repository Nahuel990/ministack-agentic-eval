"""Assertions for iam_least_privilege. Each returns (passed, expected, observed)."""
from botocore.exceptions import ClientError

from grader.policy import (Permitted, PolicyError, action_matches, allow_grants, as_list, covers, excess_grants,
                           has_wildcard, parse_policy, principals, statements)

BUCKET = "finance-001"
REPORTS = f"arn:aws:s3:::{BUCKET}/reports/"
LAMBDA = ("Service", "lambda.amazonaws.com")
LOGS_ACTIONS = {"logs:createloggroup", "logs:createlogstream", "logs:putlogevents"}


def _trusts_lambda(role) -> bool:
    try:
        return any(LAMBDA in principals(s) for s in statements(parse_policy(role["AssumeRolePolicyDocument"])))
    except PolicyError:
        return "lambda.amazonaws.com" in str(role["AssumeRolePolicyDocument"])


def _lambda_roles(ctx):
    iam = ctx.client("iam")
    roles = [r for page in iam.get_paginator("list_roles").paginate() for r in page["Roles"]]
    return [r for r in roles if _trusts_lambda(r)], roles


def _role(ctx):
    found, _ = _lambda_roles(ctx)
    return found[0] if len(found) == 1 else None


def _documents(ctx, role_name):
    """(source, document) for every inline and attached managed policy."""
    iam, docs = ctx.client("iam"), []
    for name in iam.list_role_policies(RoleName=role_name)["PolicyNames"]:
        docs.append((f"inline:{name}", parse_policy(iam.get_role_policy(RoleName=role_name, PolicyName=name)["PolicyDocument"])))
    for att in iam.list_attached_role_policies(RoleName=role_name)["AttachedPolicies"]:
        pol = iam.get_policy(PolicyArn=att["PolicyArn"])["Policy"]
        ver = iam.get_policy_version(PolicyArn=att["PolicyArn"], VersionId=pol["DefaultVersionId"])["PolicyVersion"]
        docs.append((f"managed:{att['PolicyName']}", parse_policy(ver["Document"])))
    return docs


def _grants(ctx):
    role = _role(ctx)
    if role is None:
        return None, [], "no single lambda role to inspect"
    try:
        grants, violations = allow_grants(_documents(ctx, role["RoleName"]))
    except PolicyError as e:
        return None, [], str(e)
    return grants, violations, None


def exactly_one_lambda_role(ctx):
    found, roles = _lambda_roles(ctx)
    return len(found) == 1, "exactly 1 role trusting lambda.amazonaws.com", \
        f"{len(found)} lambda role(s) {[r['RoleName'] for r in found]} among {len(roles)} role(s)"


def trust_policy_lambda_only(ctx):
    expected = "only Allow lambda.amazonaws.com sts:AssumeRole"
    role = _role(ctx)
    if role is None:
        return False, expected, "no single lambda role to inspect"
    try:
        stmts = statements(parse_policy(role["AssumeRolePolicyDocument"]))
    except PolicyError as e:
        return False, expected, str(e)
    allows = [s for s in stmts if s.get("Effect") == "Allow"]
    bad = [s for s in allows if principals(s) != {LAMBDA}
           or any(not action_matches("sts:AssumeRole", a) or has_wildcard(a) for a in as_list(s.get("Action")))
           or "NotPrincipal" in s or "NotAction" in s]
    ok = bool(allows) and not bad
    return ok, expected, f"role {role['RoleName']}: " + ("lambda-only" if ok else f"offending statements {bad or 'no Allow'}")


def required_access_granted(ctx):
    table_arn = ctx.seed["table_arn"]
    needed = [("s3:GetObject", f"{REPORTS}*"), ("dynamodb:PutItem", table_arn)]
    expected = f"grants {needed}"
    grants, _, err = _grants(ctx)
    if err:
        return False, expected, err
    missing = [n for n in needed if not covers(grants, *n)]
    return not missing, expected, f"missing: {missing}" if missing else "all required access granted"


def no_wildcard_actions(ctx):
    grants, violations, err = _grants(ctx)
    if err:
        return False, "no wildcard actions", err
    bad = [str(g) for g in grants if has_wildcard(g.action)] + violations
    return not bad, "no wildcard actions", f"wildcards: {bad}" if bad else "none"


def no_wildcard_resources(ctx):
    grants, violations, err = _grants(ctx)
    if err:
        return False, 'no Resource "*" outside CloudWatch Logs', err
    bad = [str(g) for g in grants if g.resource == "*" and g.action.lower() not in LOGS_ACTIONS] + violations
    return not bad, 'no Resource "*" outside CloudWatch Logs', f"wildcard resources: {bad}" if bad else "none"


def _reports_prefix_only(cond) -> bool:
    values = [v for op, kv in (cond or {}).items() if op in ("StringLike", "StringEquals")
              for k, vals in kv.items() if k.lower() == "s3:prefix" for v in as_list(vals)]
    return bool(values) and all(v.startswith("reports/") for v in values)


def no_excess_permissions(ctx):
    permitted = [
        Permitted({"s3:getobject"}, lambda r: r.startswith(REPORTS)),
        Permitted({"dynamodb:putitem", "dynamodb:updateitem", "dynamodb:batchwriteitem"}, lambda r: r == ctx.seed["table_arn"]),
        Permitted({"s3:listbucket"}, lambda r: r == f"arn:aws:s3:::{BUCKET}", _reports_prefix_only),
        Permitted(LOGS_ACTIONS, lambda r: r == "*" or r.startswith("arn:aws:logs:")),
    ]
    expected = "only s3:GetObject on finance-001/reports/*, item writes on invoices, (+ standard logs)"
    grants, violations, err = _grants(ctx)
    if err:
        return False, expected, err
    bad = [str(g) for g in excess_grants(grants, permitted)] + violations
    return not bad, expected, f"broader than needed: {bad}" if bad else "nothing excess"


def seeded_resources_intact(ctx):
    problems = []
    s3, ddb = ctx.client("s3"), ctx.client("dynamodb")
    try:
        keys = sorted(o["Key"] for o in s3.list_objects_v2(Bucket=BUCKET).get("Contents", []))
        if keys != ctx.seed["objects"]:
            problems.append(f"finance-001 objects now {keys}")
    except ClientError as e:
        problems.append(f"finance-001: {e.response['Error'].get('Code')}")
    try:
        if ddb.describe_table(TableName="invoices")["Table"].get("TableId") != ctx.seed["table_id"]:
            problems.append("invoices table was recreated (TableId changed)")
    except ClientError as e:
        problems.append(f"invoices: {e.response['Error'].get('Code')}")
    return not problems, "seeded bucket objects and invoices table unchanged", "; ".join(problems) or "intact"


ASSERTIONS = {
    "exactly_one_lambda_role": exactly_one_lambda_role,
    "trust_policy_lambda_only": trust_policy_lambda_only,
    "required_access_granted": required_access_granted,
    "no_wildcard_actions": no_wildcard_actions,
    "no_wildcard_resources": no_wildcard_resources,
    "no_excess_permissions": no_excess_permissions,
    "seeded_resources_intact": seeded_resources_intact,
}
