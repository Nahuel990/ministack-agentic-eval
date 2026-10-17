"""The boto3 reference solution proves the grader; this proves each task is also
solvable through the MCP tools the agent actually gets (allowlist applied), e.g.
that aws_execute's command filter doesn't block it. Requires MiniStack; resets it."""
import asyncio
import json

import pytest
from mcp import ClientSession
from mcp.client.stdio import stdio_client

from grader.aws import AwsContext, endpoint_url, reset_environment
from grader.core import grade
from runner.agent import _mcp_server_params
from runner.task import all_task_ids, load_task

ACCT = "000000000000"
THUMBS_ARN = f"arn:aws:sqs:us-east-1:{ACCT}:thumbnails-q"
TOPIC_ARN = f"arn:aws:sns:us-east-1:{ACCT}:order-events"


def j(obj) -> str:
    """Single-quoted JSON for a CLI argument (shlex keeps it verbatim)."""
    return "'" + json.dumps(obj) + "'"


def queue_attrs(policy: dict) -> str:
    return j({"Policy": json.dumps(policy)})


def sns_policy(queue: str) -> dict:
    return {"Version": "2012-10-17", "Statement": [{
        "Effect": "Allow", "Principal": {"Service": "sns.amazonaws.com"}, "Action": "sqs:SendMessage",
        "Resource": f"arn:aws:sqs:us-east-1:{ACCT}:{queue}",
        "Condition": {"ArnEquals": {"aws:SourceArn": TOPIC_ARN}}}]}


COMMANDS = {
    "s3_logs_bucket": [
        "aws s3api create-bucket --bucket app-logs-001",
        "aws s3api put-public-access-block --bucket app-logs-001 --public-access-block-configuration "
        "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true",
        "aws s3api put-bucket-lifecycle-configuration --bucket app-logs-001 --lifecycle-configuration "
        + j({"Rules": [{"ID": "expire-30d", "Status": "Enabled", "Filter": {"Prefix": ""}, "Expiration": {"Days": 30}}]}),
    ],
    "s3_lifecycle_add_rule": [
        "aws s3api put-bucket-lifecycle-configuration --bucket app-data-001 --lifecycle-configuration " + j({"Rules": [
            {"ID": "archive-logs", "Status": "Enabled", "Filter": {"Prefix": "logs/"}, "Transitions": [{"Days": 90, "StorageClass": "GLACIER"}]},
            {"ID": "expire-cache", "Status": "Enabled", "Filter": {"Prefix": "cache/"}, "Expiration": {"Days": 14}},
            {"ID": "expire-tmp", "Status": "Enabled", "Filter": {"Prefix": "tmp/"}, "Expiration": {"Days": 7}},
        ]}),
    ],
    "s3_policy_add_statement": [
        "aws s3api put-bucket-policy --bucket reports-001 --policy " + j({"Version": "2012-10-17", "Statement": [
            {"Sid": "AnalyticsRead", "Effect": "Allow", "Principal": {"AWS": f"arn:aws:iam::{ACCT}:role/analytics-reader"},
             "Action": "s3:GetObject", "Resource": "arn:aws:s3:::reports-001/*"},
            {"Sid": "DenyInsecureTransport", "Effect": "Deny", "Principal": "*", "Action": "s3:*",
             "Resource": ["arn:aws:s3:::reports-001", "arn:aws:s3:::reports-001/*"],
             "Condition": {"Bool": {"aws:SecureTransport": "false"}}},
        ]}),
    ],
    "s3_notification_add": [
        "aws sqs create-queue --queue-name thumbnails-q",
        f"aws sqs set-queue-attributes --queue-url http://localhost:4566/{ACCT}/thumbnails-q --attributes " + queue_attrs(
            {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": "s3.amazonaws.com"},
             "Action": "sqs:SendMessage", "Resource": THUMBS_ARN,
             "Condition": {"ArnEquals": {"aws:SourceArn": "arn:aws:s3:::uploads-001"}}}]}),
        "aws s3api put-bucket-notification-configuration --bucket uploads-001 --notification-configuration " + j({"QueueConfigurations": [
            {"Id": "ingest-incoming", "QueueArn": f"arn:aws:sqs:us-east-1:{ACCT}:ingest-q", "Events": ["s3:ObjectCreated:*"],
             "Filter": {"Key": {"FilterRules": [{"Name": "prefix", "Value": "incoming/"}]}}},
            {"Id": "thumbnails-images", "QueueArn": THUMBS_ARN, "Events": ["s3:ObjectCreated:*"],
             "Filter": {"Key": {"FilterRules": [{"Name": "prefix", "Value": "images/"}]}}},
        ]}),
    ],
    "sns_sqs_fanout": [
        "aws sns create-topic --name order-events",
        *[c for q in ("billing-q", "shipping-q") for c in (
            f"aws sqs create-queue --queue-name {q}",
            f"aws sqs set-queue-attributes --queue-url http://localhost:4566/{ACCT}/{q} --attributes " + queue_attrs(sns_policy(q)),
            f"aws sns subscribe --topic-arn {TOPIC_ARN} --protocol sqs --notification-endpoint arn:aws:sqs:us-east-1:{ACCT}:{q}",
        )],
    ],
    "iam_least_privilege": [
        "aws iam create-role --role-name finance-report-invoice-writer --assume-role-policy-document " + j(
            {"Version": "2012-10-17", "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}]}),
        "aws iam put-role-policy --role-name finance-report-invoice-writer --policy-name access --policy-document " + j(
            {"Version": "2012-10-17", "Statement": [
                {"Effect": "Allow", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::finance-001/reports/*"},
                {"Effect": "Allow", "Action": "dynamodb:PutItem", "Resource": f"arn:aws:dynamodb:us-east-1:{ACCT}:table/invoices"}]}),
    ],
    "dynamodb_add_gsi": [
        "aws dynamodb update-table --table-name customers --attribute-definitions AttributeName=email,AttributeType=S "
        "--global-secondary-index-updates " + j([{"Create": {"IndexName": "email-index",
            "KeySchema": [{"AttributeName": "email", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}}}]),
    ],
}


async def _run(task, commands):
    async with stdio_client(_mcp_server_params()) as (r, w), ClientSession(r, w) as session:
        await session.initialize()
        names = {t.name for t in (await session.list_tools()).tools}
        assert "aws_execute" in names and task.allows_tool("aws_execute")
        outputs = []
        for cmd in commands:
            res = await session.call_tool("aws_execute", {"command": cmd})
            outputs.append(json.loads(res.content[0].text))
        return outputs


def test_every_task_has_an_mcp_solution():
    assert set(COMMANDS) == set(all_task_ids())


@pytest.mark.parametrize("task_id", sorted(COMMANDS))
def test_task_solvable_via_mcp(task_id):
    if endpoint_url() is None:
        pytest.skip("MINISTACK_ENDPOINT_URL unset")
    reset_environment()
    task = load_task(task_id)
    ctx = AwsContext()
    task.prepare(ctx)
    for out in asyncio.run(_run(task, COMMANDS[task_id])):
        assert out.get("exit_code") == 0, out
    result = grade(task, ctx)
    assert result.passed, [a.message for a in result.assertions]
