"""Unit tests for the static policy checker (no MiniStack needed)."""
import json
import urllib.parse

import pytest

from grader.policy import (Permitted, PolicyError, allow_grants, covers, equivalent, excess_grants, parse_policy,
                           principals, service_can_send)

Q = "arn:aws:sqs:us-east-1:000000000000:billing-q"
T = "arn:aws:sns:us-east-1:000000000000:order-events"


def doc(*stmts):
    return {"Version": "2012-10-17", "Statement": list(stmts)}


def test_parse_policy_forms():
    d = doc({"Effect": "Allow", "Action": "s3:GetObject", "Resource": "*"})
    assert parse_policy(d) == d
    assert parse_policy(json.dumps(d)) == d
    assert parse_policy(urllib.parse.quote(json.dumps(d))) == d
    with pytest.raises(PolicyError):
        parse_policy("{bad")


def test_principals_normalisation():
    assert principals({"Principal": "*"}) == {("*", "*")}
    assert principals({"Principal": {"AWS": "*"}}) == {("*", "*")}
    assert principals({"Principal": {"Service": ["a.amazonaws.com", "b.amazonaws.com"]}}) == {
        ("Service", "a.amazonaws.com"), ("Service", "b.amazonaws.com")}


def test_equivalent_ignores_sid_list_form_and_action_case():
    a = {"Sid": "X", "Effect": "Allow", "Principal": {"AWS": "arn:r"}, "Action": "s3:GetObject", "Resource": "arn:b/*"}
    b = {"Effect": "Allow", "Principal": {"AWS": ["arn:r"]}, "Action": ["S3:getobject"], "Resource": ["arn:b/*"]}
    assert equivalent(a, b)
    assert not equivalent(a, b | {"Resource": "arn:b/x/*"})


def sns_allow(**extra):
    return {"Effect": "Allow", "Principal": {"Service": "sns.amazonaws.com"}, "Action": "sqs:SendMessage", "Resource": Q, **extra}


@pytest.mark.parametrize("policy,require,expected", [
    (None, True, False),
    (doc(sns_allow(Condition={"ArnEquals": {"aws:SourceArn": T}})), True, True),
    (doc(sns_allow(Condition={"ArnLike": {"aws:SourceArn": "arn:aws:sns:*:000000000000:order-*"}})), True, True),
    (doc(sns_allow()), True, False),                       # SourceArn required by task
    (doc(sns_allow()), False, True),                       # but AWS would deliver
    (doc(sns_allow(Condition={"ArnEquals": {"aws:SourceArn": T + "-other"}})), True, False),
    (doc(sns_allow(Principal="*", Condition={"ArnEquals": {"aws:SourceArn": T}})), True, True),
    (doc(sns_allow(Principal={"Service": "s3.amazonaws.com"}, Condition={"ArnEquals": {"aws:SourceArn": T}})), True, False),
    (doc(sns_allow(Action="sqs:*", Resource="*", Condition={"ArnEquals": {"aws:SourceArn": T}})), True, True),
    (doc(sns_allow(Condition={"ArnEquals": {"aws:SourceArn": T}}), {"Effect": "Deny", "Principal": "*", "Action": "sqs:*", "Resource": Q}), True, False),
    (doc(sns_allow(Condition={"IpAddress": {"aws:SourceIp": "1.2.3.4"}})), False, False),  # unsupported -> not granted
])
def test_service_can_send(policy, require, expected):
    ok, why = service_can_send(policy and json.dumps(policy), service="sns.amazonaws.com", action="sqs:SendMessage",
                               resource_arn=Q, source_arn=T, require_source_arn=require)
    assert ok is expected, why


def test_allow_grants_and_coverage():
    grants, violations = allow_grants([("inline", doc(
        {"Effect": "Allow", "Action": ["s3:*"], "Resource": "*"},
        {"Effect": "Deny", "Action": "s3:DeleteObject", "Resource": "*"},
        {"Effect": "Allow", "NotAction": "iam:*", "Resource": "*"},
    ))])
    assert [str(g) for g in grants] == ["s3:* on * [inline]"]
    assert len(violations) == 1 and "NotAction" in violations[0]
    assert covers(grants, "s3:GetObject", "arn:aws:s3:::finance-001/reports/x")
    assert not covers(grants, "dynamodb:PutItem", "arn:aws:dynamodb:us-east-1:0:table/t")


def test_excess_grants():
    ok = Permitted({"s3:getobject"}, lambda r: r.startswith("arn:aws:s3:::finance-001/reports/"))
    grants, _ = allow_grants([("p", doc(
        {"Effect": "Allow", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::finance-001/reports/*"},
        {"Effect": "Allow", "Action": "s3:Get*", "Resource": "arn:aws:s3:::finance-001/reports/*"},
        {"Effect": "Allow", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::finance-001/*"},
        {"Effect": "Allow", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::finance-001/reports*"},
    ))])
    assert [g.resource for g in excess_grants(grants, [ok])] == [
        "arn:aws:s3:::finance-001/reports/*", "arn:aws:s3:::finance-001/*", "arn:aws:s3:::finance-001/reports*"]
