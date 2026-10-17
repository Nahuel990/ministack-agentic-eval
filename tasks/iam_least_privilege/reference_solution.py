"""Lambda-only trust, an inline policy scoped to exactly what's needed, plus AWS's
standard basic-execution policy for logs."""
import json

ROLE = "finance-report-invoice-writer"


def solve(ctx):
    iam, ddb = ctx.client("iam"), ctx.client("dynamodb")
    table_arn = ddb.describe_table(TableName="invoices")["Table"]["TableArn"]
    iam.create_role(RoleName=ROLE, AssumeRolePolicyDocument=json.dumps({
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}],
    }))
    iam.put_role_policy(RoleName=ROLE, PolicyName="reports-read-invoices-write", PolicyDocument=json.dumps({
        "Version": "2012-10-17",
        "Statement": [
            {"Effect": "Allow", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::finance-001/reports/*"},
            {"Effect": "Allow", "Action": "dynamodb:PutItem", "Resource": table_arn},
        ],
    }))
    iam.attach_role_policy(RoleName=ROLE, PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole")
