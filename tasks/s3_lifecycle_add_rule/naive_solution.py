"""Plausible wrong approach: PUT a configuration containing only the new rule,
which replaces (deletes) the two existing rules."""

BUCKET = "app-data-001"
EXPECTED_FAILURES = {"rule_count_is_3", "archive_logs_unchanged", "expire_cache_unchanged"}


def solve(ctx):
    ctx.client("s3").put_bucket_lifecycle_configuration(
        Bucket=BUCKET,
        LifecycleConfiguration={"Rules": [{"ID": "expire-tmp", "Status": "Enabled", "Filter": {"Prefix": "tmp/"}, "Expiration": {"Days": 7}}]},
    )
