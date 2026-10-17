"""Add the GSI in place with UpdateTable and wait for it to become ACTIVE."""
import time

TABLE = "customers"


def solve(ctx):
    ddb = ctx.client("dynamodb")
    ddb.update_table(
        TableName=TABLE,
        AttributeDefinitions=[{"AttributeName": "email", "AttributeType": "S"}],
        GlobalSecondaryIndexUpdates=[{"Create": {
            "IndexName": "email-index",
            "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
            "Projection": {"ProjectionType": "ALL"},
        }}],
    )
    deadline = time.monotonic() + 900  # real AWS backfill can take minutes
    while time.monotonic() < deadline:
        gsis = ddb.describe_table(TableName=TABLE)["Table"].get("GlobalSecondaryIndexes", [])
        if any(g["IndexName"] == "email-index" and g.get("IndexStatus") == "ACTIVE" for g in gsis):
            return
        time.sleep(5)
    raise TimeoutError("email-index did not become ACTIVE")
