"""Plausible wrong approach: PUT a policy containing only the Deny, which replaces
(deletes) the existing analytics-reader grant."""
import json

BUCKET = "reports-001"
EXPECTED_FAILURES = {"analytics_read_preserved"}


def solve(ctx):
    ctx.client("s3").put_bucket_policy(Bucket=BUCKET, Policy=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "DenyInsecureTransport",
            "Effect": "Deny",
            "Principal": "*",
            "Action": "s3:*",
            "Resource": [f"arn:aws:s3:::{BUCKET}", f"arn:aws:s3:::{BUCKET}/*"],
            "Condition": {"Bool": {"aws:SecureTransport": "false"}},
        }],
    }))
