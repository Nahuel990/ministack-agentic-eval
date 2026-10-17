"""Brownfield: a populated customers table keyed by customer_id."""

TABLE = "customers"
PLANS = ("free", "pro", "enterprise")


def seed_items() -> list[dict]:
    return [{
        "customer_id": {"S": f"cus_{i:04d}"},
        "email": {"S": f"customer{i:04d}@example.com"},
        "name": {"S": f"Customer {i:04d}"},
        "plan": {"S": PLANS[i % 3]},
        "signup_year": {"N": str(2019 + i % 7)},
    } for i in range(50)]


def setup(ctx):
    ddb = ctx.client("dynamodb")
    ddb.create_table(
        TableName=TABLE,
        AttributeDefinitions=[{"AttributeName": "customer_id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "customer_id", "KeyType": "HASH"}],
        BillingMode="PAY_PER_REQUEST",
    )
    ddb.get_waiter("table_exists").wait(TableName=TABLE)
    items = seed_items()
    for item in items:
        ddb.put_item(TableName=TABLE, Item=item)
    t = ddb.describe_table(TableName=TABLE)["Table"]
    return {"table_id": t.get("TableId"), "creation": t["CreationDateTime"].isoformat(), "items": items}
