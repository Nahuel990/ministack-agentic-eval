"""Brownfield: a data bucket that already has two lifecycle rules and some objects."""

BUCKET = "app-data-001"
RULES = [
    {"ID": "archive-logs", "Status": "Enabled", "Filter": {"Prefix": "logs/"},
     "Transitions": [{"Days": 90, "StorageClass": "GLACIER"}]},
    {"ID": "expire-cache", "Status": "Enabled", "Filter": {"Prefix": "cache/"},
     "Expiration": {"Days": 14}},
]


def setup(ctx):
    s3 = ctx.client("s3")
    s3.create_bucket(Bucket=BUCKET)
    for key in ("logs/2026-10-01/app.log", "cache/session-4f2a.json", "tmp/export-123.csv", "data/customers.parquet"):
        s3.put_object(Bucket=BUCKET, Key=key, Body=b"seed")
    s3.put_bucket_lifecycle_configuration(Bucket=BUCKET, LifecycleConfiguration={"Rules": RULES})
    # Snapshot exactly what the backend stores, so "unchanged" is judged against it.
    return {"rules": s3.get_bucket_lifecycle_configuration(Bucket=BUCKET)["Rules"]}
