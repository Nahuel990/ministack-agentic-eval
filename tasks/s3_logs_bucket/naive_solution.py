"""Plausible wrong approach: "disable" versioning with Status=Disabled. Real AWS
rejects it (only Enabled|Suspended exist) with MalformedXML, and so does MiniStack
since 1.5.35. A script run with `set -e` stops there, so the bucket is left
without public access blocking or a lifecycle rule."""

from botocore.exceptions import ClientError

BUCKET = "app-logs-001"
EXPECTED_FAILURES = {"public_access_fully_blocked", "lifecycle_expires_30_days"}


def solve(ctx):
    s3 = ctx.client("s3")
    s3.create_bucket(Bucket=BUCKET)
    try:
        s3.put_bucket_versioning(Bucket=BUCKET, VersioningConfiguration={"Status": "Disabled"})
    except ClientError:
        return
    s3.put_public_access_block(
        Bucket=BUCKET,
        PublicAccessBlockConfiguration={k: True for k in ("BlockPublicAcls", "IgnorePublicAcls", "BlockPublicPolicy", "RestrictPublicBuckets")},
    )
    s3.put_bucket_lifecycle_configuration(
        Bucket=BUCKET,
        LifecycleConfiguration={"Rules": [{"ID": "expire-30d", "Status": "Enabled", "Filter": {"Prefix": ""}, "Expiration": {"Days": 30}}]},
    )
