"""Brownfield: uploads bucket already feeding incoming/ objects to an ingest queue."""
import json

BUCKET = "uploads-001"
BUCKET_ARN = f"arn:aws:s3:::{BUCKET}"


def queue_policy(queue_arn: str) -> str:
    return json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Sid": "AllowS3Uploads",
            "Effect": "Allow",
            "Principal": {"Service": "s3.amazonaws.com"},
            "Action": "sqs:SendMessage",
            "Resource": queue_arn,
            "Condition": {"ArnEquals": {"aws:SourceArn": BUCKET_ARN}},
        }],
    })


def setup(ctx):
    s3, sqs = ctx.client("s3"), ctx.client("sqs")
    s3.create_bucket(Bucket=BUCKET)
    url = sqs.create_queue(QueueName="ingest-q")["QueueUrl"]
    arn = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    sqs.set_queue_attributes(QueueUrl=url, Attributes={"Policy": queue_policy(arn)})
    s3.put_bucket_notification_configuration(Bucket=BUCKET, NotificationConfiguration={"QueueConfigurations": [{
        "Id": "ingest-incoming",
        "QueueArn": arn,
        "Events": ["s3:ObjectCreated:*"],
        "Filter": {"Key": {"FilterRules": [{"Name": "prefix", "Value": "incoming/"}]}},
    }]})
    s3.put_object(Bucket=BUCKET, Key="images/logo.png", Body=b"seed")
    config = s3.get_bucket_notification_configuration(Bucket=BUCKET)["QueueConfigurations"][0]
    policy = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["Policy"])["Attributes"]["Policy"]
    return {"ingest_config": config, "ingest_policy": json.loads(policy), "ingest_arn": arn}
