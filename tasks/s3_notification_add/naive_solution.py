"""Plausible wrong approach: create the queue correctly, then PUT a notification
configuration containing only the new queue, which removes the ingest-q feed."""
import json

BUCKET = "uploads-001"
EXPECTED_FAILURES = {"ingest_config_preserved", "incoming_upload_reaches_ingest_q"}


def solve(ctx):
    s3, sqs = ctx.client("s3"), ctx.client("sqs")
    url = sqs.create_queue(QueueName="thumbnails-q")["QueueUrl"]
    arn = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    sqs.set_queue_attributes(QueueUrl=url, Attributes={"Policy": json.dumps({
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": "s3.amazonaws.com"},
                       "Action": "sqs:SendMessage", "Resource": arn,
                       "Condition": {"ArnEquals": {"aws:SourceArn": f"arn:aws:s3:::{BUCKET}"}}}],
    })})
    s3.put_bucket_notification_configuration(Bucket=BUCKET, NotificationConfiguration={"QueueConfigurations": [{
        "Id": "thumbnails-images",
        "QueueArn": arn,
        "Events": ["s3:ObjectCreated:*"],
        "Filter": {"Key": {"FilterRules": [{"Name": "prefix", "Value": "images/"}]}},
    }]})
