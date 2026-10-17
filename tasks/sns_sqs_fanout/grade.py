"""Assertions for sns_sqs_fanout. Each returns (passed, expected, observed).
Static assertions first; the behavioural one publishes and reads queues."""
import time
import uuid

from botocore.exceptions import ClientError

from grader.policy import PolicyError, equivalent, parse_policy, service_can_send, statements

TOPIC = "order-events"
QUEUES = ("billing-q", "shipping-q")


def _topic_arn(ctx, name):
    sns = ctx.client("sns")
    for page in sns.get_paginator("list_topics").paginate():
        for t in page["Topics"]:
            if t["TopicArn"].rsplit(":", 1)[-1] == name:
                return t["TopicArn"]
    return None


def _queue(ctx, name):
    sqs = ctx.client("sqs")
    try:
        url = sqs.get_queue_url(QueueName=name)["QueueUrl"]
    except ClientError:
        return None
    attrs = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn", "Policy"])["Attributes"]
    return url, attrs["QueueArn"], attrs.get("Policy")


def _sqs_endpoints(ctx, topic_arn):
    sns = ctx.client("sns")
    subs = [s for page in sns.get_paginator("list_subscriptions_by_topic").paginate(TopicArn=topic_arn)
            for s in page["Subscriptions"]]
    return {s["Endpoint"] for s in subs if s["Protocol"] == "sqs"}


def resources_exist(ctx):
    missing = ([TOPIC] if not _topic_arn(ctx, TOPIC) else []) + [q for q in QUEUES if _queue(ctx, q) is None]
    return not missing, f"topic {TOPIC}, queues {list(QUEUES)}", f"missing: {missing}" if missing else "all present"


def both_queues_subscribed(ctx):
    expected = f"SQS subscriptions on {TOPIC} for {list(QUEUES)}"
    topic = _topic_arn(ctx, TOPIC)
    if not topic:
        return False, expected, f"topic {TOPIC} does not exist"
    endpoints = _sqs_endpoints(ctx, topic)
    missing = [q for q in QUEUES if (_queue(ctx, q) or (None, None))[1] not in endpoints]
    return not missing, expected, f"not subscribed: {missing}; sqs endpoints: {sorted(endpoints)}" if missing else "both subscribed"


def _policy_allows_topic(ctx, queue_name):
    expected = f"{queue_name} policy allows sns.amazonaws.com sqs:SendMessage with aws:SourceArn = {TOPIC} ARN"
    topic, q = _topic_arn(ctx, TOPIC), _queue(ctx, queue_name)
    if not topic or q is None:
        return False, expected, "topic or queue missing"
    ok, why = service_can_send(q[2], service="sns.amazonaws.com", action="sqs:SendMessage",
                               resource_arn=q[1], source_arn=topic, require_source_arn=True)
    return ok, expected, why


def billing_policy_allows_topic(ctx):
    return _policy_allows_topic(ctx, "billing-q")


def shipping_policy_allows_topic(ctx):
    return _policy_allows_topic(ctx, "shipping-q")


def seeded_inventory_fanout_intact(ctx):
    seed = ctx.seed
    expected = "inventory-events topic, its inventory-q subscription and inventory-q policy unchanged"
    problems = []
    topic = _topic_arn(ctx, "inventory-events")
    if topic != seed["inventory_topic"]:
        problems.append(f"topic now {topic}")
    elif seed["inventory_queue_arn"] not in _sqs_endpoints(ctx, topic):
        problems.append("inventory-q subscription removed")
    q = _queue(ctx, "inventory-q")
    if q is None:
        problems.append("inventory-q deleted")
    else:
        try:
            now = statements(parse_policy(q[2])) if q[2] else []
        except PolicyError as e:
            now, _ = [], problems.append(str(e))
        was = statements(seed["inventory_policy"])
        if not (len(now) == len(was) and all(any(equivalent(a, b) for b in now) for a in was)):
            problems.append(f"inventory-q policy changed: {q[2]}")
    return not problems, expected, "; ".join(problems) or "intact"


def publish_reaches_both_queues(ctx):
    token = f"grader-{uuid.uuid4().hex}"
    expected = f"message {token} received on {list(QUEUES)}"
    topic = _topic_arn(ctx, TOPIC)
    queues = {name: _queue(ctx, name) for name in QUEUES}
    if not topic or None in queues.values():
        return False, expected, "topic or queue missing"
    ctx.client("sns").publish(TopicArn=topic, Message=token)
    sqs, got = ctx.client("sqs"), set()
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline and got != set(QUEUES):
        for name, (url, _, _) in queues.items():
            if name in got:
                continue
            for m in sqs.receive_message(QueueUrl=url, MaxNumberOfMessages=10, WaitTimeSeconds=1).get("Messages", []):
                if token in m["Body"]:
                    got.add(name)
    missing = sorted(set(QUEUES) - got)
    return not missing, expected, f"not received within 8s on: {missing}" if missing else "received on both"


ASSERTIONS = {
    "resources_exist": resources_exist,
    "both_queues_subscribed": both_queues_subscribed,
    "billing_policy_allows_topic": billing_policy_allows_topic,
    "shipping_policy_allows_topic": shipping_policy_allows_topic,
    "seeded_inventory_fanout_intact": seeded_inventory_fanout_intact,
    "publish_reaches_both_queues": publish_reaches_both_queues,
}
