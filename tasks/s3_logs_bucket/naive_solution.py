"""Plausible wrong approach: "disable" versioning with Status=Disabled. MiniStack
accepts it; real AWS rejects it (only Enabled|Suspended exist)."""

BUCKET = "app-logs-001"
EXPECTED_FAILURES = {"versioning_not_enabled"}


def solve(ctx):
    s3 = ctx.client("s3")
    s3.create_bucket(Bucket=BUCKET)
    s3.put_bucket_versioning(Bucket=BUCKET, VersioningConfiguration={"Status": "Disabled"})
    s3.put_public_access_block(
        Bucket=BUCKET,
        PublicAccessBlockConfiguration={k: True for k in ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")},
    )
    s3.put_bucket_lifecycle_configuration(
        Bucket=BUCKET,
        LifecycleConfiguration={"Rules": [{"ID": "expire-30d", "Status": "Enabled", "Filter": {"Prefix": ""}, "Expiration": {"Days": 30}}]},
    )
