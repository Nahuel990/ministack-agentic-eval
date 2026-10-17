"""Assertions for dynamodb_add_gsi. Each returns (passed, expected, observed)."""
import json

from botocore.exceptions import ClientError

TABLE = "customers"


def _table(ctx):
    try:
        return ctx.client("dynamodb").describe_table(TableName=TABLE)["Table"], None
    except ClientError as e:
        return None, f"DescribeTable failed: {e.response['Error'].get('Code')}"


def _email_index(table):
    for g in table.get("GlobalSecondaryIndexes", []):
        if any(k["AttributeName"] == "email" and k["KeyType"] == "HASH" for k in g["KeySchema"]):
            return g
    return None


def _scan(ctx):
    ddb, items, kwargs = ctx.client("dynamodb"), [], {"TableName": TABLE}
    while True:
        page = ddb.scan(**kwargs)
        items += page["Items"]
        if "LastEvaluatedKey" not in page:
            return items
        kwargs["ExclusiveStartKey"] = page["LastEvaluatedKey"]


def table_not_recreated(ctx):
    expected = f"TableId={ctx.seed['table_id']}, CreationDateTime={ctx.seed['creation']}"
    t, err = _table(ctx)
    if err:
        return False, expected, err
    observed = f"TableId={t.get('TableId')}, CreationDateTime={t['CreationDateTime'].isoformat()}"
    ok = t.get("TableId") == ctx.seed["table_id"] and t["CreationDateTime"].isoformat() == ctx.seed["creation"]
    return ok, expected, observed


def email_gsi_active(ctx):
    expected = "GSI with HASH key email, IndexStatus ACTIVE"
    t, err = _table(ctx)
    if err:
        return False, expected, err
    g = _email_index(t)
    gsis = [(x["IndexName"], x["KeySchema"], x.get("IndexStatus")) for x in t.get("GlobalSecondaryIndexes", [])]
    return bool(g) and g.get("IndexStatus") == "ACTIVE", expected, f"GSIs: {gsis or 'none'}"


def email_lookup_works(ctx):
    samples = [ctx.seed["items"][i] for i in (0, 17, 49)]
    expected = f"query by email returns the matching customer for {[s['email']['S'] for s in samples]}"
    t, err = _table(ctx)
    if err:
        return False, expected, err
    g = _email_index(t)
    if not g:
        return False, expected, "no GSI keyed on email"
    wrong = []
    for s in samples:
        items = ctx.client("dynamodb").query(
            TableName=TABLE, IndexName=g["IndexName"], KeyConditionExpression="email = :e",
            ExpressionAttributeValues={":e": s["email"]},
        )["Items"]
        ids = [i["customer_id"]["S"] for i in items]
        if ids != [s["customer_id"]["S"]]:
            wrong.append(f"{s['email']['S']} -> {ids}")
    return not wrong, expected, f"wrong results: {wrong}" if wrong else "all lookups correct"


def still_50_items(ctx):
    t, err = _table(ctx)
    if err:
        return False, "50 items", err
    n = len(_scan(ctx))
    return n == 50, "50 items", f"{n} items"


def items_unchanged(ctx):
    expected = "every seeded item present and identical"
    t, err = _table(ctx)
    if err:
        return False, expected, err
    current = {i["customer_id"]["S"]: i for i in _scan(ctx)}
    seeded = {i["customer_id"]["S"]: i for i in ctx.seed["items"]}
    missing = sorted(set(seeded) - set(current))
    changed = sorted(k for k in set(seeded) & set(current) if current[k] != seeded[k])
    extra = sorted(set(current) - set(seeded))
    ok = not (missing or changed or extra)
    observed = "identical" if ok else (
        f"missing {len(missing)} {missing[:5]}, changed {len(changed)} "
        f"{[json.dumps(current[k], sort_keys=True) for k in changed[:2]]}, extra {len(extra)} {extra[:5]}")
    return ok, expected, observed


ASSERTIONS = {
    "table_not_recreated": table_not_recreated,
    "email_gsi_active": email_gsi_active,
    "email_lookup_works": email_lookup_works,
    "still_50_items": still_50_items,
    "items_unchanged": items_unchanged,
}
