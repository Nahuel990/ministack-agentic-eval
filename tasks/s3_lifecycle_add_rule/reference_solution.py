"""Read-modify-write: keep the existing rules, append the new one."""

BUCKET = "app-data-001"


def solve(ctx):
    s3 = ctx.client("s3")
    rules = s3.get_bucket_lifecycle_configuration(Bucket=BUCKET)["Rules"]
    rules.append({"ID": "expire-tmp", "Status": "Enabled", "Filter": {"Prefix": "tmp/"}, "Expiration": {"Days": 7}})
    s3.put_bucket_lifecycle_configuration(Bucket=BUCKET, LifecycleConfiguration={"Rules": rules})
