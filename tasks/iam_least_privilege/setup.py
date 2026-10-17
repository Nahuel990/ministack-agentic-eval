"""Brownfield: a finance bucket with reports and other sensitive data, and an invoices table."""

BUCKET = "finance-001"
OBJECTS = ("reports/2026-09.csv", "reports/2026-10.csv", "payroll/2026-10.csv", "audit/ledger-2026.xlsx")


def setup(ctx):
    s3, ddb = ctx.client("s3"), ctx.client("dynamodb")
    s3.create_bucket(Bucket=BUCKET)
    for key in OBJECTS:
        s3.put_object(Bucket=BUCKET, Key=key, Body=b"seed")
    ddb.create_table(
        TableName="invoices",
        AttributeDefinitions=[{"AttributeName": "invoice_id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "invoice_id", "KeyType": "HASH"}],
        BillingMode="PAY_PER_REQUEST",
    )
    table = ddb.describe_table(TableName="invoices")["Table"]
    return {"objects": sorted(OBJECTS), "table_arn": table["TableArn"], "table_id": table.get("TableId")}
