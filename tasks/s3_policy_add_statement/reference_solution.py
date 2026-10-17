"""Read-modify-write: keep the existing statement, add an HTTPS-only Deny."""
import json

BUCKET = "reports-001"


def solve(ctx):
    s3 = ctx.client("s3")
    policy = json.loads(s3.get_bucket_policy(Bucket=BUCKET)["Policy"])
    policy["Statement"].append({
        "Sid": "DenyInsecureTransport",
        "Effect": "Deny",
        "Principal": "*",
        "Action": "s3:*",
        "Resource": [f"arn:aws:s3:::{BUCKET}", f"arn:aws:s3:::{BUCKET}/*"],
        "Condition": {"Bool": {"aws:SecureTransport": "false"}},
    })
    s3.put_bucket_policy(Bucket=BUCKET, Policy=json.dumps(policy))
