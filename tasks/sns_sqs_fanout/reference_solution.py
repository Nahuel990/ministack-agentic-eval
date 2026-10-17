"""Topic + queues + subscriptions, and a queue policy per queue scoped to the topic."""
import json


def solve(ctx):
    sns, sqs = ctx.client("sns"), ctx.client("sqs")
    topic = sns.create_topic(Name="order-events")["TopicArn"]
    for name in ("billing-q", "shipping-q"):
        url = sqs.create_queue(QueueName=name)["QueueUrl"]
        arn = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
        sqs.set_queue_attributes(QueueUrl=url, Attributes={"Policy": json.dumps({
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Principal": {"Service": "sns.amazonaws.com"},
                "Action": "sqs:SendMessage",
                "Resource": arn,
                "Condition": {"ArnEquals": {"aws:SourceArn": topic}},
            }],
        })})
        sns.subscribe(TopicArn=topic, Protocol="sqs", Endpoint=arn)
