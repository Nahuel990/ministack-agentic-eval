"""Loads tasks/<task_id>/task.yaml and the task's optional Python modules."""
from __future__ import annotations

import importlib.util
from dataclasses import dataclass, field
from pathlib import Path

import yaml

TASKS_DIR = Path(__file__).resolve().parent.parent / "tasks"


@dataclass
class Task:
    id: str
    dir: Path
    prompt: str
    max_turns: int
    max_tool_calls: int
    assertions: list[dict]
    aws_operations: dict[str, list[str]]
    tools_allow: list[str] | None = None  # None = every MCP tool
    tools_deny: list[str] = field(default_factory=list)
    fidelity_notes: list[str] = field(default_factory=list)

    def has_module(self, name: str) -> bool:
        return (self.dir / f"{name}.py").exists()

    def load_module(self, name: str):
        path = self.dir / f"{name}.py"
        spec = importlib.util.spec_from_file_location(f"tasks.{self.id}.{name}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def prepare(self, ctx) -> dict:
        """Run setup.py (if any) and remember its snapshot on ctx for the grader."""
        ctx.seed = (self.load_module("setup").setup(ctx) or {}) if self.has_module("setup") else {}
        return ctx.seed

    def allows_tool(self, name: str) -> bool:
        if self.tools_allow is not None and name not in self.tools_allow:
            return False
        return name not in self.tools_deny


def load_task(task_id: str) -> Task:
    d = TASKS_DIR / task_id
    raw = yaml.safe_load((d / "task.yaml").read_text())
    if raw["id"] != task_id:
        raise ValueError(f"{d}/task.yaml has id {raw['id']!r}, expected {task_id!r}")
    tools = raw.get("tools") or {}
    return Task(
        id=raw["id"],
        dir=d,
        prompt=raw["prompt"].strip(),
        max_turns=int(raw["max_turns"]),
        max_tool_calls=int(raw["max_tool_calls"]),
        assertions=raw["assertions"],
        aws_operations=raw["aws_operations"],
        tools_allow=tools.get("allow"),
        tools_deny=tools.get("deny") or [],
        fidelity_notes=raw.get("fidelity_notes") or [],
    )


def all_task_ids() -> list[str]:
    return sorted(p.parent.name for p in TASKS_DIR.glob("*/task.yaml"))
