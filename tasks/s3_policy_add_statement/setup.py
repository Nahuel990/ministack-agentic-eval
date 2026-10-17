"""Brownfield: a reports bucket whose policy already grants an analytics role read access."""
import json

BUCKET = "reports-001"
POLICY = {
    "Version": "2012-10-17",
    "Statement": [{
        "Sid": "AnalyticsRead",
        "Effect": "Allow",
        "Principal": {"AWS": "arn:aws:iam::000000000000:role/analytics-reader"},
        "Action": "s3:GetObject",
        "Resource": "arn:aws:s3:::reports-001/*",
    }],
}


def setup(ctx):
    s3 = ctx.client("s3")
    s3.create_bucket(Bucket=BUCKET)
    for key in ("monthly/2026-09.pdf", "monthly/2026-10.pdf"):
        s3.put_object(Bucket=BUCKET, Key=key, Body=b"seed")
    s3.put_bucket_policy(Bucket=BUCKET, Policy=json.dumps(POLICY))
    return {"policy": json.loads(s3.get_bucket_policy(Bucket=BUCKET)["Policy"])}
