"""Plausible wrong approach: create and subscribe, but never give the queues a
policy that lets SNS deliver. Real AWS silently drops every message."""

EXPECTED_FAILURES = {"billing_policy_allows_topic", "shipping_policy_allows_topic"}


def solve(ctx):
    sns, sqs = ctx.client("sns"), ctx.client("sqs")
    topic = sns.create_topic(Name="order-events")["TopicArn"]
    for name in ("billing-q", "shipping-q"):
        url = sqs.create_queue(QueueName=name)["QueueUrl"]
        arn = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn"])["Attributes"]["QueueArn"]
        sns.subscribe(TopicArn=topic, Protocol="sqs", Endpoint=arn)
