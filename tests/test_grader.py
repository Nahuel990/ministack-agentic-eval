"""Grader self-checks against a live MiniStack: hand-built correct state must PASS,
hand-built wrong state must FAIL with a clear observed-vs-expected message.

These tests reset MiniStack. They refuse to run when MINISTACK_ENDPOINT_URL is
unset, so they never touch real AWS.
"""
import pytest

from grader.aws import AwsContext, endpoint_url, reset_environment
from grader.core import grade
from runner.parity import undeclared_operations
from runner.task import load_task

BUCKET = "app-logs-001"
ALL_BLOCKED = dict(BlockPublicAcls=True, IgnorePublicAcls=True, BlockPublicPolicy=True, RestrictPublicBuckets=True)


@pytest.fixture
def ctx():
    if endpoint_url() is None:
        pytest.skip("MINISTACK_ENDPOINT_URL unset; grader tests only run against MiniStack")
    reset_environment()
    return AwsContext()


@pytest.fixture
def task():
    return load_task("s3_logs_bucket")


def by_id(result):
    return {a.id: a for a in result.assertions}


def make_bucket(ctx, *, days=30, rule_status="Enabled", versioning=None, pab=ALL_BLOCKED):
    s3 = ctx.client("s3")
    s3.create_bucket(Bucket=BUCKET)
    if versioning:
        s3.put_bucket_versioning(Bucket=BUCKET, VersioningConfiguration={"Status": versioning})
    if pab:
        s3.put_public_access_block(Bucket=BUCKET, PublicAccessBlockConfiguration=pab)
    if days is not None:
        s3.put_bucket_lifecycle_configuration(
            Bucket=BUCKET,
            LifecycleConfiguration={"Rules": [{"ID": "r1", "Status": rule_status, "Filter": {"Prefix": ""}, "Expiration": {"Days": days}}]},
        )


def test_correct_bucket_passes(ctx, task):
    make_bucket(ctx)
    result = grade(task, ctx)
    assert result.passed, [a.message for a in result.assertions]
    assert not result.grader_error


def test_wrong_bucket_fails_with_clear_messages(ctx, task):
    make_bucket(ctx, days=7, versioning="Enabled")
    result = grade(task, ctx)
    a = by_id(result)
    assert not result.passed and not result.grader_error
    assert {x.id for x in result.failed} == {"versioning_not_enabled", "lifecycle_expires_30_days"}
    assert "Status=Enabled" in a["versioning_not_enabled"].observed
    assert "Days': 7" in a["lifecycle_expires_30_days"].observed
    assert "Expiration.Days=30" in a["lifecycle_expires_30_days"].expected


def test_missing_bucket_fails_every_assertion(ctx, task):
    result = grade(task, ctx)
    assert not result.passed and not result.grader_error
    assert len(result.failed) == 4
    assert "HeadBucket failed" in by_id(result)["bucket_exists"].observed


def test_partial_public_access_block_names_the_flag(ctx, task):
    make_bucket(ctx, pab=ALL_BLOCKED | {"RestrictPublicBuckets": False})
    result = grade(task, ctx)
    assert [x.id for x in result.failed] == ["public_access_fully_blocked"]
    assert "not true: RestrictPublicBuckets" in result.failed[0].observed


def test_missing_public_access_block_fails(ctx, task):
    make_bucket(ctx, pab=None)
    result = grade(task, ctx)
    assert [x.id for x in result.failed] == ["public_access_fully_blocked"]
    assert "NoSuchPublicAccessBlockConfiguration" in result.failed[0].observed


def test_disabled_lifecycle_rule_fails(ctx, task):
    make_bucket(ctx, rule_status="Disabled")
    result = grade(task, ctx)
    assert [x.id for x in result.failed] == ["lifecycle_expires_30_days"]
    assert "Status=Disabled" in result.failed[0].observed


def test_suspended_versioning_counts_as_not_enabled(ctx, task):
    make_bucket(ctx, versioning="Suspended")
    assert grade(task, ctx).passed


def test_reference_solution_passes_using_only_declared_operations(ctx, task):
    task.load_module("reference_solution").solve(ctx)
    result = grade(task, ctx)
    assert result.passed, [a.message for a in result.assertions]
    assert undeclared_operations(ctx.operations_called, task.aws_operations) == []
