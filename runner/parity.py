"""Checks a task's declared AWS operations against the installed ministack-mcp's
parity.json (service status) and catalog.json (per-operation list).

parity.json only carries a status per service; the per-operation list lives in
catalog.json, which is what ministack-mcp's own is_operation_supported tool uses.
An operation counts as supported when its service is `full` or `partial` in
parity.json AND the operation is listed for that service in catalog.json.
"""
from __future__ import annotations

import json
from importlib import metadata, util
from pathlib import Path

SUPPORTED_STATUSES = {"full", "partial"}


def _load(name: str) -> dict:
    # Locate the package without importing it: importing ministack_mcp builds its
    # FastMCP server, which reconfigures root logging for the whole harness.
    pkg_dir = Path(util.find_spec("ministack_mcp").submodule_search_locations[0])
    return json.loads((pkg_dir / name).read_text())


def check_operations(aws_operations: dict[str, list[str]]) -> dict:
    parity = _load("parity.json")["services"]
    catalog = _load("catalog.json")
    problems, checked = [], []
    for service, ops in aws_operations.items():
        status = parity.get(service, {}).get("status", "absent")
        catalog_ops = set(catalog["services"].get(service, {}).get("operations", []))
        if status not in SUPPORTED_STATUSES:
            problems.append(f"{service}: parity.json status is {status!r}")
        for op in ops:
            if op not in catalog_ops:
                problems.append(f"{service}:{op} not in catalog.json")
            checked.append(f"{service}:{op}")
    return {
        "ok": not problems,
        "problems": problems,
        "checked": checked,
        "ministack_mcp_version": metadata.version("ministack-mcp"),
        "catalog_ministack_version": catalog.get("ministack_version"),
    }


def undeclared_operations(called: set[tuple[str, str]], aws_operations: dict[str, list[str]]) -> list[str]:
    """Operations actually issued via boto3 that the task did not declare."""
    return sorted(f"{s}:{o}" for s, o in called if o not in aws_operations.get(s, []))
