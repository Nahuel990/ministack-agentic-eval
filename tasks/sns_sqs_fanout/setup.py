"""Brownfield: an unrelated, working inventory fan-out already exists in the account."""
import json


def sns_queue_policy(queue_arn: str, topic_arn: str) -> str:
    return json.dumps({
        "Version": "2012-10-17",
        "Statement": [{
            "Effect": "Allow",
            "Principal": {"Service": "sns.amazonaws.com"},
            "Action": "sqs:SendMessage",
            "Resource": queue_arn,
            "Condition": {"ArnEquals": {"aws:SourceArn": topic_arn}},
        }],
    })


def setup(ctx):
    sns, sqs = ctx.client("sns"), ctx.client("sqs")
    topic = sns.create_topic(Name="inventory-events")["TopicArn"]
    url = sqs.create_queue(QueueName="inventory-q")["QueueUrl"]
    arn = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
    sqs.set_queue_attributes(QueueUrl=url, Attributes={"Policy": sns_queue_policy(arn, topic)})
    sns.subscribe(TopicArn=topic, Protocol="sqs", Endpoint=arn)
    policy = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["Policy"])["Attributes"]["Policy"]
    return {"inventory_topic": topic, "inventory_queue_arn": arn, "inventory_policy": json.loads(policy)}
