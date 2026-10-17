"""Known-good boto3 solution; must PASS grade.py (run via run_eval.py --reference)."""

BUCKET = "app-logs-001"


def solve(ctx):
    s3 = ctx.client("s3")
    region = s3.meta.region_name
    kwargs = {} if region in (None, "us-east-1") else {"CreateBucketConfiguration": {"LocationConstraint": region}}
    s3.create_bucket(Bucket=BUCKET, **kwargs)
    # New buckets have versioning unset (disabled), so nothing to do for versioning.
    s3.put_public_access_block(
        Bucket=BUCKET,
        PublicAccessBlockConfiguration={
            "BlockPublicAcls": True,
            "IgnorePublicAcls": True,
            "BlockPublicPolicy": True,
            "RestrictPublicBuckets": True,
        },
    )
    s3.put_bucket_lifecycle_configuration(
        Bucket=BUCKET,
        LifecycleConfiguration={
            "Rules": [{"ID": "expire-30d", "Status": "Enabled", "Filter": {"Prefix": ""}, "Expiration": {"Days": 30}}]
        },
    )
