"""Offline checks: task definitions, parity, tool filtering, schema conversion."""
from types import SimpleNamespace

import pytest

from runner.agent import mcp_to_openai, safe_name
from runner.parity import check_operations
from runner.task import all_task_ids, load_task


@pytest.mark.parametrize("task_id", all_task_ids())
def test_task_is_well_formed_and_parity_supported(task_id):
    task = load_task(task_id)
    grade_ids = set(task.load_module("grade").ASSERTIONS)
    assert {a["id"] for a in task.assertions} == grade_ids
    assert task.has_module("reference_solution")
    report = check_operations(task.aws_operations)
    assert report["ok"], report["problems"]


def test_parity_flags_unknown_operations():
    report = check_operations({"s3": ["CreateBucket", "MadeUpOperation"], "notaservice": ["X"]})
    assert not report["ok"]
    assert "s3:MadeUpOperation not in catalog.json" in report["problems"]
    assert any(p.startswith("notaservice:") for p in report["problems"])


def test_tool_filtering():
    task = load_task("s3_logs_bucket")
    assert task.allows_tool("aws_execute")
    assert not task.allows_tool("ministack_reset")
    assert not task.allows_tool("run_smoke_test")  # not in allowlist


def test_mcp_to_openai_schema():
    tool = SimpleNamespace(name="aws_execute", description=" run ", inputSchema={"properties": {"command": {"type": "string"}}})
    out = mcp_to_openai(tool)
    assert out["function"]["parameters"]["type"] == "object"
    assert out["function"]["description"] == "run"
    assert safe_name("openai/gpt-oss-20b:free") == "openai_gpt-oss-20b_free"
