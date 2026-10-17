"""Create thumbnails-q with a policy S3 can use, then read-modify-write the
notification configuration so the existing ingest-q entry is kept."""
import json

BUCKET = "uploads-001"


def solve(ctx):
    s3, sqs = ctx.client("s3"), ctx.client("sqs")
    url = sqs.create_queue(QueueName="thumbnails-q")["QueueUrl"]
    arn = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    sqs.set_queue_attributes(QueueUrl=url, Attributes={"Policy": json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "s3.amazonaws.com"},
            "Action": "sqs:SendMessage",
            "Resource": arn,
            "Condition": {"ArnEquals": {"aws:SourceArn": f"arn:aws:s3:::{BUCKET}"}},
        }],
    })})
    config = s3.get_bucket_notification_configuration(Bucket=BUCKET)
    config.pop("ResponseMetadata", None)
    config.setdefault("QueueConfigurations", []).append({
        "Id": "thumbnails-images",
        "QueueArn": arn,
        "Events": ["s3:ObjectCreated:*"],
        "Filter": {"Key": {"FilterRules": [{"Name": "prefix", "Value": "images/"}]}},
    })
    s3.put_bucket_notification_configuration(Bucket=BUCKET, NotificationConfiguration=config)
