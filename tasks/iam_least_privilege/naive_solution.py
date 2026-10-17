"""Plausible wrong approach: AmazonS3FullAccess plus PutItem on Resource "*".
It works, and grants read/write on every bucket (including finance-001/payroll/)."""
import json

ROLE = "finance-lambda-role"
EXPECTED_FAILURES = {"no_wildcard_actions", "no_wildcard_resources", "no_excess_permissions"}


def solve(ctx):
    iam = ctx.client("iam")
    iam.create_role(RoleName=ROLE, AssumeRolePolicyDocument=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}],
    }))
    iam.attach_role_policy(RoleName=ROLE, PolicyArn="arn:aws:iam::aws:policy/AmazonS3FullAccess")
    iam.put_role_policy(RoleName=ROLE, PolicyName="invoices", PolicyDocument=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "dynamodb:PutItem", "Resource": "*"}],
    }))
