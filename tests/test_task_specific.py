"""Variants of the trap that the generic naive solutions don't cover. Requires MiniStack."""
import pytest

from grader.aws import AwsContext, endpoint_url, reset_environment
from grader.core import grade
from runner.task import load_task


@pytest.fixture
def seeded():
    if endpoint_url() is None:
        pytest.skip("MINISTACK_ENDPOINT_URL unset")

    def _seed(task_id):
        reset_environment()
        task = load_task(task_id)
        ctx = AwsContext()
        task.prepare(ctx)
        return task, ctx
    return _seed


def test_gsi_recreate_and_reload_is_still_caught(seeded):
    """Back up, recreate with the GSI, reload all 50 items within the same second:
    data is identical and CreationDateTime may match, but TableId changes."""
    task, ctx = seeded("dynamodb_add_gsi")
    task.load_module("naive_solution").solve(ctx)
    ddb = ctx.client("dynamodb")
    for item in ctx.seed["items"]:
        ddb.put_item(TableName="customers", Item=item)
    result = grade(task, ctx)
    assert {a.id for a in result.failed} == {"table_not_recreated"}, [a.message for a in result.assertions]
    assert "TableId=" in result.failed[0].observed


def test_lifecycle_rule_modified_in_place_is_caught(seeded):
    task, ctx = seeded("s3_lifecycle_add_rule")
    s3 = ctx.client("s3")
    rules = s3.get_bucket_lifecycle_configuration(Bucket="app-data-001")["Rules"]
    rules[1]["Expiration"]["Days"] = 7  # "fixes" expire-cache instead of adding a rule
    rules.append({"ID": "expire-tmp", "Status": "Enabled", "Filter": {"Prefix": "tmp/"}, "Expiration": {"Days": 7}})
    s3.put_bucket_lifecycle_configuration(Bucket="app-data-001", LifecycleConfiguration={"Rules": rules})
    result = grade(task, ctx)
    assert {a.id for a in result.failed} == {"expire_cache_unchanged"}
    assert "'Days': 7" in result.failed[0].observed or '"Days": 7' in result.failed[0].observed


def test_bucket_policy_https_deny_missing_bucket_arn_is_caught(seeded):
    import json
    task, ctx = seeded("s3_policy_add_statement")
    s3 = ctx.client("s3")
    policy = json.loads(s3.get_bucket_policy(Bucket="reports-001")["Policy"])
    policy["Statement"].append({"Effect": "Deny", "Principal": "*", "Action": "s3:*",
                                "Resource": "arn:aws:s3:::reports-001/*",
                                "Condition": {"Bool": {"aws:SecureTransport": "false"}}})
    s3.put_bucket_policy(Bucket="reports-001", Policy=json.dumps(policy))
    result = grade(task, ctx)
    assert {a.id for a in result.failed} == {"deny_insecure_transport"}
    assert "not covered: ['arn:aws:s3:::reports-001']" in result.failed[0].observed
