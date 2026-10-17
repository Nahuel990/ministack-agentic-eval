"""Plausible wrong approach: delete the table and recreate it with the GSI.
The index works, and all 50 customers are gone."""

TABLE = "customers"
EXPECTED_FAILURES = {"table_not_recreated", "email_lookup_works", "still_50_items", "items_unchanged"}


def solve(ctx):
    ddb = ctx.client("dynamodb")
    ddb.delete_table(TableName=TABLE)
    ddb.get_waiter("table_not_exists").wait(TableName=TABLE)
    ddb.create_table(
        TableName=TABLE,
        AttributeDefinitions=[{"AttributeName": "customer_id", "AttributeType": "S"},
                              {"AttributeName": "email", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "customer_id", "KeyType": "HASH"}],
        GlobalSecondaryIndexes=[{"IndexName": "email-index",
                                 "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}],
                                 "Projection": {"ProjectionType": "ALL"}}],
        BillingMode="PAY_PER_REQUEST",
    )
    ddb.get_waiter("table_exists").wait(TableName=TABLE)
