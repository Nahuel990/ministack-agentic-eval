"""Assertions for s3_notification_add. Each returns (passed, expected, observed).
Static assertions first; the behavioural ones upload objects and read queues."""
import json
import time
import uuid

from botocore.exceptions import ClientError

from grader.policy import PolicyError, equivalent, parse_policy, service_can_send, statements

BUCKET = "uploads-001"
BUCKET_ARN = f"arn:aws:s3:::{BUCKET}"
CREATED_SUBTYPES = {"s3:ObjectCreated:Put", "s3:ObjectCreated:Post", "s3:ObjectCreated:Copy",
                    "s3:ObjectCreated:CompleteMultipartUpload"}


def _configs(ctx):
    try:
        return ctx.client("s3").get_bucket_notification_configuration(Bucket=BUCKET).get("QueueConfigurations", []), None
    except ClientError as e:
        return None, f"GetBucketNotificationConfiguration failed: {e.response['Error'].get('Code')}"


def _queue(ctx, name):
    """(url, arn, policy-or-None) or None if the queue doesn't exist."""
    sqs = ctx.client("sqs")
    try:
        url = sqs.get_queue_url(QueueName=name)["QueueUrl"]
    except ClientError:
        return None
    attrs = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["QueueArn", "Policy"])["Attributes"]
    return url, attrs["QueueArn"], attrs.get("Policy")


def _filter_rules(cfg):
    rules = cfg.get("Filter", {}).get("Key", {}).get("FilterRules", [])
    return sorted((r["Name"].lower(), r["Value"]) for r in rules)


def _all_created(events):
    events = set(events)
    return "s3:ObjectCreated:*" in events or CREATED_SUBTYPES <= events


def _brief(configs):
    return [{"QueueArn": c.get("QueueArn"), "Events": c.get("Events"), "Filter": _filter_rules(c)} for c in configs]


def ingest_config_preserved(ctx):
    seeded = ctx.seed["ingest_config"]
    expected = f"config {_brief([seeded])[0]}"
    configs, err = _configs(ctx)
    if err:
        return False, expected, err
    ok = any(c.get("QueueArn") == seeded["QueueArn"] and set(c.get("Events", [])) == set(seeded["Events"])
             and _filter_rules(c) == _filter_rules(seeded) for c in configs)
    return ok, expected, f"queue configs: {_brief(configs)}"


def ingest_queue_policy_intact(ctx):
    expected = "ingest-q policy equivalent to the seeded one"
    q = _queue(ctx, "ingest-q")
    if q is None:
        return False, expected, "ingest-q does not exist"
    try:
        current = parse_policy(q[2]) if q[2] else {}
    except PolicyError as e:
        return False, expected, str(e)
    seeded, now = statements(ctx.seed["ingest_policy"]), statements(current)
    ok = len(seeded) == len(now) and all(any(equivalent(s, n) for n in now) for s in seeded)
    return ok, expected, "unchanged" if ok else f"policy now: {json.dumps(current)}"


def thumbnails_config_added(ctx):
    expected = "config: thumbnails-q, all ObjectCreated events, filter exactly prefix=images/"
    q = _queue(ctx, "thumbnails-q")
    if q is None:
        return False, expected, "queue thumbnails-q does not exist"
    configs, err = _configs(ctx)
    if err:
        return False, expected, err
    ok = any(c.get("QueueArn") == q[1] and _all_created(c.get("Events", []))
             and _filter_rules(c) == [("prefix", "images/")] for c in configs)
    return ok, expected, f"queue configs: {_brief(configs)}"


def thumbnails_policy_allows_s3(ctx):
    expected = f"thumbnails-q policy allows s3.amazonaws.com sqs:SendMessage from {BUCKET_ARN}"
    q = _queue(ctx, "thumbnails-q")
    if q is None:
        return False, expected, "queue thumbnails-q does not exist"
    ok, why = service_can_send(q[2], service="s3.amazonaws.com", action="sqs:SendMessage",
                               resource_arn=q[1], source_arn=BUCKET_ARN, require_source_arn=False)
    return ok, expected, why


def _upload_reaches(ctx, prefix, queue_name, suffix):
    key = f"{prefix}grader-{uuid.uuid4().hex}{suffix}"
    expected = f"an ObjectCreated event for {key} on {queue_name}"
    q = _queue(ctx, queue_name)
    if q is None:
        return False, expected, f"queue {queue_name} does not exist"
    ctx.client("s3").put_object(Bucket=BUCKET, Key=key, Body=b"grader probe")
    sqs, seen = ctx.client("sqs"), 0
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        for m in sqs.receive_message(QueueUrl=q[0], MaxNumberOfMessages=10, WaitTimeSeconds=1).get("Messages", []):
            seen += 1
            if key in m["Body"]:
                return True, expected, "event received"
    return False, expected, f"no event for {key} within 8s ({seen} other message(s) seen)"


def incoming_upload_reaches_ingest_q(ctx):
    return _upload_reaches(ctx, "incoming/", "ingest-q", ".csv")


def images_upload_reaches_thumbnails_q(ctx):
    return _upload_reaches(ctx, "images/", "thumbnails-q", ".jpg")


ASSERTIONS = {
    "ingest_config_preserved": ingest_config_preserved,
    "ingest_queue_policy_intact": ingest_queue_policy_intact,
    "thumbnails_config_added": thumbnails_config_added,
    "thumbnails_policy_allows_s3": thumbnails_policy_allows_s3,
    "incoming_upload_reaches_ingest_q": incoming_upload_reaches_ingest_q,
    "images_upload_reaches_thumbnails_q": images_upload_reaches_thumbnails_q,
}
