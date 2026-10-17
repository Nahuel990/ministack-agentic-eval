"""Run the eval: reset -> setup -> agent (or reference solution) -> grade -> report.

  python run_eval.py --task s3_logs_bucket --model <model>   # one task, agent
  python run_eval.py --model <model> --trials 3              # full suite, agent, 3 trials per task
  python run_eval.py --reference                             # full suite, reference solutions
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")
for noisy in ("httpx", "botocore", "boto3"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

from grader.aws import AwsContext, endpoint_url, reset_environment  # noqa: E402
from grader.core import grade  # noqa: E402
from runner.parity import check_operations, undeclared_operations  # noqa: E402
from runner.task import all_task_ids, load_task  # noqa: E402

RESULTS_DIR = ROOT / "results"


def rel(p: str | None) -> str | None:
    if not p:
        return p
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return p


def run_task(task_id: str, model: str | None, reference: bool, trial: int = 1) -> dict:
    task = load_task(task_id)
    started = time.monotonic()
    row: dict = {
        "task": task.id, "trial": trial,
        "model": "reference" if reference else model,
        "mode": "reference" if reference else "agent",
    }

    parity = check_operations(task.aws_operations)
    row["parity"] = parity
    if not parity["ok"]:
        row.update(status="skipped", error=f"unsupported operations: {parity['problems']}")
        return row

    row["reset"] = reset_environment()
    ctx = AwsContext()
    row["seed"] = task.prepare(ctx)

    if reference:
        task.load_module("reference_solution").solve(ctx)
        row["agent"] = None
    else:
        from runner.agent import run_agent

        agent = asyncio.run(run_agent(task, model))
        row["agent"] = agent.to_dict() | {"transcript_path": rel(agent.transcript_path)}
        row["model"] = agent.model

    result = grade(task, ctx)
    row["grade"] = result.to_dict()
    row["passed"] = result.passed
    row["failed_assertions"] = [a.id for a in result.failed]
    row["undeclared_aws_operations"] = undeclared_operations(ctx.operations_called, task.aws_operations)
    row["false_success"] = bool(row["agent"] and row["agent"]["claimed_success"] and not result.passed)
    if row["agent"] and row["agent"]["stop_reason"].startswith("error"):
        row["status"] = "agent_error"  # infra/API failure, not a model result; excluded from pass rates
    else:
        row["status"] = "grader_error" if result.grader_error else "graded"
    row["duration_s"] = round(time.monotonic() - started, 1)
    return row


def aggregate(rows: list[dict]) -> list[dict]:
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in rows:
        groups[(r["task"], r["model"])].append(r)
    out = []
    for (task, model), all_rs in groups.items():
        rs = [r for r in all_rs if r.get("status") in ("graded", "grader_error")]
        agents = [r["agent"] for r in rs if r.get("agent")]
        n = len(rs)
        if not n:
            out.append({"task": task, "model": model, "trials": 0, "excluded": len(all_rs), "passed": 0, "pass_rate": None,
                        "claimed_success": None, "false_success": None, "mean_turns": None, "mean_tool_calls": None})
            continue
        out.append({
            "task": task, "model": model, "trials": n, "excluded": len(all_rs) - n,
            "passed": sum(bool(r.get("passed")) for r in rs),
            "pass_rate": round(sum(bool(r.get("passed")) for r in rs) / n, 3),
            "claimed_success": sum(a["claimed_success"] for a in agents) if agents else None,
            "false_success": sum(bool(r.get("false_success")) for r in rs) if agents else None,
            "mean_turns": round(sum(a["turns"] for a in agents) / len(agents), 1) if agents else None,
            "mean_tool_calls": round(sum(a["tool_calls"] for a in agents) / len(agents), 1) if agents else None,
        })
    return out


def markdown(rows: list[dict], agg: list[dict]) -> str:
    agent_rows = [r for r in rows if r.get("agent")]
    false_successes = sum(bool(r.get("false_success")) for r in rows)
    lines = []
    if agent_rows:
        lines.append(f"**False success: {false_successes}/{len(agent_rows)} runs** (agent claimed done, grader failed)\n")
    lines += [
        "| task | model | graded trials | pass rate | claimed success | false success | mean turns | mean tool calls | excluded (agent_error/not_run) |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    na = lambda v: "n/a" if v is None else v  # noqa: E731
    for g in agg:
        rate = f"{g['passed']}/{g['trials']} ({g['pass_rate']:.0%})" if g["trials"] else "n/a"
        lines.append(f"| {g['task']} | {g['model']} | {g['trials']} | {rate} "
                     f"| {na(g['claimed_success'])} | {na(g['false_success'])} | {na(g['mean_turns'])} | {na(g['mean_tool_calls'])} | {g['excluded']} |")
    lines += [
        "\nPer run:\n",
        "| task | trial | model | result | failed assertions | agent claimed success | false success | turns | tool calls | stop reason |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        a = r.get("agent")
        if r.get("status") in ("skipped", "not_run", "agent_error"):
            result = r["status"].upper()
        else:
            result = "PASS" if r.get("passed") else ("ERROR" if r.get("status") == "grader_error" else "FAIL")
        lines.append("| {} | {} | {} | {} | {} | {} | {} | {} | {} | {} |".format(
            r["task"], r["trial"], r["model"], result,
            ", ".join(r.get("failed_assertions", [])) or "-",
            ("y" if a["claimed_success"] else f"n ({a['claim']})") if a else "n/a",
            ("**YES**" if r.get("false_success") else "no") if a else "n/a",
            a["turns"] if a else "-", a["tool_calls"] if a else "-",
            a["stop_reason"] if a else "-",
        ))
    failures = [(r, x) for r in rows for x in r.get("grade", {}).get("assertions", []) if not x["passed"]]
    if failures:
        lines.append("\nFailed assertions:\n")
        lines += [f"- `{r['task']}` #{r['trial']} / `{r['model']}`: {x['message']}" for r, x in failures]
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--task", action="append", help="task id (repeatable); default: all tasks")
    ap.add_argument("--model", help="model id; default: $EVAL_MODEL")
    ap.add_argument("--reference", action="store_true", help="run reference_solution.py instead of the agent")
    ap.add_argument("--trials", type=int, default=1, help="independent runs per task (default 1)")
    args = ap.parse_args()

    if endpoint_url() is None:
        print("WARNING: MINISTACK_ENDPOINT_URL unset -> grading against real AWS via the default "
              "credential chain. ministack-mcp tools still target MiniStack, so agent runs only make "
              "sense with MiniStack.", file=sys.stderr)

    rows, quota_exhausted = [], False
    # Trial-major order: every task gets trial 1 before any task gets trial 2.
    for trial in range(1, args.trials + 1):
        for task_id in args.task or all_task_ids():
            if quota_exhausted:
                rows.append({"task": task_id, "trial": trial, "model": args.model, "mode": "agent", "status": "not_run",
                             "agent": None, "error": "skipped: provider request quota exhausted earlier in this run"})
                continue
            print(f"== {task_id} #{trial} ({'reference' if args.reference else 'agent'})", file=sys.stderr)
            row = run_task(task_id, args.model, args.reference, trial)
            rows.append(row)
            for x in row.get("grade", {}).get("assertions", []):
                print("   " + x["message"], file=sys.stderr)
            if row.get("status") == "agent_error":
                print(f"   agent error: {row['agent']['stop_reason']}", file=sys.stderr)
                quota_exhausted = "RateLimitError" in row["agent"]["stop_reason"] or "429" in row["agent"]["stop_reason"]

    agg = aggregate(rows)
    RESULTS_DIR.mkdir(exist_ok=True)
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "endpoint": endpoint_url() or "real AWS (default chain)",
        "mode": "reference" if args.reference else "agent",
        "trials": args.trials,
        "totals": {
            "runs": len(rows),
            "passed": sum(bool(r.get("passed")) for r in rows),
            "false_success": sum(bool(r.get("false_success")) for r in rows),
            "grader_errors": sum(r.get("status") == "grader_error" for r in rows),
            "skipped": sum(r.get("status") == "skipped" for r in rows),
            "agent_errors": sum(r.get("status") == "agent_error" for r in rows),
            "not_run": sum(r.get("status") == "not_run" for r in rows),
        },
        "per_task_model": agg,
        "fidelity_notes": {t: load_task(t).fidelity_notes for t in sorted({r["task"] for r in rows})},
        "results": rows,
    }
    (RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2, default=str))
    md = markdown(rows, agg)
    (RESULTS_DIR / "summary.md").write_text(md)
    print(md)
    for r in rows:
        if r.get("agent"):
            print(f"transcript: {r['agent']['transcript_path']}")
    print("summary: results/summary.json, results/summary.md")

    # In reference mode every run must pass: a failure means an unsolvable task or a false-fail grader.
    if args.reference and summary["totals"]["passed"] != len(rows):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
