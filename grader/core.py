"""Runs a task's deterministic assertions and reports per-assertion results."""
from __future__ import annotations

import traceback
from dataclasses import asdict, dataclass

from grader.aws import AwsContext


@dataclass
class AssertionResult:
    id: str
    description: str
    passed: bool
    expected: str
    observed: str
    error: str | None = None  # set when the assertion itself crashed (grader problem, not agent problem)

    @property
    def message(self) -> str:
        status = "PASS" if self.passed else ("ERROR" if self.error else "FAIL")
        return f"[{status}] {self.id}: expected {self.expected}; observed {self.observed}"


@dataclass
class GradeResult:
    passed: bool
    grader_error: bool
    assertions: list[AssertionResult]

    @property
    def failed(self) -> list[AssertionResult]:
        return [a for a in self.assertions if not a.passed]

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "grader_error": self.grader_error,
            "assertions": [asdict(a) | {"message": a.message} for a in self.assertions],
        }


def grade(task, ctx: AwsContext | None = None) -> GradeResult:
    """Each assertion in grade.py is `fn(ctx) -> (passed, expected, observed)`.
    The task passes only if every assertion listed in task.yaml passes."""
    ctx = ctx or AwsContext()
    module = task.load_module("grade")
    available = getattr(module, "ASSERTIONS", {})
    results = []
    for spec in task.assertions:
        fn = available.get(spec["id"])
        if fn is None:
            results.append(AssertionResult(spec["id"], spec.get("description", ""), False, "assertion implemented in grade.py", "missing", error="not implemented"))
            continue
        try:
            passed, expected, observed = fn(ctx)
            results.append(AssertionResult(spec["id"], spec.get("description", ""), bool(passed), str(expected), str(observed)))
        except Exception as e:  # noqa: BLE001 - a crashing check must not crash the run
            results.append(AssertionResult(spec["id"], spec.get("description", ""), False, "assertion to run", f"{type(e).__name__}: {e}", error=traceback.format_exc()))
    return GradeResult(
        passed=bool(results) and all(r.passed for r in results),
        grader_error=any(r.error for r in results),
        assertions=results,
    )
