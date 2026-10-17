"""For every task: reference_solution.py must PASS and naive_solution.py must FAIL
on exactly its EXPECTED_FAILURES, each with an observed-vs-expected message.
Requires MiniStack; resets it."""
import pytest

from grader.aws import AwsContext, endpoint_url, reset_environment
from grader.core import grade
from runner.parity import undeclared_operations
from runner.task import all_task_ids, load_task


def _run(task_id, module):
    if endpoint_url() is None:
        pytest.skip("MINISTACK_ENDPOINT_URL unset; solution tests only run against MiniStack")
    reset_environment()
    task = load_task(task_id)
    ctx = AwsContext()
    task.prepare(ctx)
    solution = task.load_module(module)
    solution.solve(ctx)
    return task, ctx, solution, grade(task, ctx)


@pytest.mark.parametrize("task_id", all_task_ids())
def test_reference_solution_passes(task_id):
    task, ctx, _, result = _run(task_id, "reference_solution")
    assert result.passed, [a.message for a in result.assertions]
    assert undeclared_operations(ctx.operations_called, task.aws_operations) == []


@pytest.mark.parametrize("task_id", all_task_ids())
def test_naive_solution_fails_as_expected(task_id):
    task, ctx, naive, result = _run(task_id, "naive_solution")
    failed = {a.id for a in result.failed}
    assert not result.passed and not result.grader_error, [a.message for a in result.assertions]
    assert failed == naive.EXPECTED_FAILURES, [a.message for a in result.failed]
    for a in result.failed:
        assert a.expected and a.observed, a.message
    assert undeclared_operations(ctx.operations_called, task.aws_operations) == []
