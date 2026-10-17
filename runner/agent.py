"""Tool-calling agent that drives MiniStack only through ministack-mcp (stdio).

Model, base URL and API key come from env vars:
  EVAL_MODEL     model id (run_eval.py --model overrides)
  EVAL_BASE_URL  OpenAI-compatible base URL (default: OpenRouter)
  EVAL_API_KEY   API key (falls back to OPENROUTER_API_KEY)
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import OpenAI

from runner.task import Task

DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
MAX_RESULT_CHARS_TO_MODEL = 6000
RUNS_DIR = Path(__file__).resolve().parent.parent / "runs"

SYSTEM_PROMPT = """You are an infrastructure agent working in an AWS-compatible cloud environment.
You can only act on the environment through the provided tools. There is no human in the loop:
do not ask questions, make reasonable decisions and carry the goal through.
When you are finished, call the `finish` tool exactly once:
  status "done"   - you believe the goal is fully met
  status "failed" - you could not fully meet the goal
with a short summary of what you did."""

FINISH_TOOL = {
    "type": "function",
    "function": {
        "name": "finish",
        "description": "Report that you are finished and whether the goal was achieved. Ends the session.",
        "parameters": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["done", "failed"]},
                "summary": {"type": "string"},
            },
            "required": ["status", "summary"],
        },
    },
}

NUDGE = "You have not called the `finish` tool. Continue working if needed, otherwise call `finish` now."


@dataclass
class AgentResult:
    model: str
    claim: str  # "done" | "failed" | "no_claim"
    claim_summary: str
    stop_reason: str  # finished | max_turns | max_tool_calls | no_finish | error: ...
    turns: int
    tool_calls: int
    blocked_tool_calls: int
    usage: dict
    transcript_path: str

    @property
    def claimed_success(self) -> bool:
        return self.claim == "done"

    def to_dict(self) -> dict:
        return asdict(self) | {"claimed_success": self.claimed_success}


class Transcript:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._f = path.open("w")
        self._seq = 0

    def log(self, event: str, **data) -> None:
        self._seq += 1
        rec = {"seq": self._seq, "ts": datetime.now(timezone.utc).isoformat(), "event": event, **data}
        self._f.write(json.dumps(rec, default=str) + "\n")
        self._f.flush()

    def close(self) -> None:
        self._f.close()


def llm_config(model: str | None) -> dict:
    model = model or os.environ.get("EVAL_MODEL")
    api_key = os.environ.get("EVAL_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if not model:
        raise SystemExit("No model: pass --model or set EVAL_MODEL")
    if not api_key:
        raise SystemExit("No API key: set EVAL_API_KEY (or OPENROUTER_API_KEY)")
    return {"model": model, "base_url": os.environ.get("EVAL_BASE_URL") or DEFAULT_BASE_URL, "api_key": api_key}


def safe_name(s: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", s)


def mcp_to_openai(tool) -> dict:
    params = dict(tool.inputSchema or {})
    params.setdefault("type", "object")
    params.setdefault("properties", {})
    return {
        "type": "function",
        "function": {"name": tool.name, "description": (tool.description or "").strip(), "parameters": params},
    }


def _mcp_server_params() -> StdioServerParameters:
    # The MCP SDK only forwards HOME/PATH/etc. by default; the server (and the aws
    # CLI it shells out to) needs the endpoint and AWS settings. Model API keys are
    # deliberately not forwarded to the tool process.
    env = {k: v for k, v in os.environ.items() if k not in {"EVAL_API_KEY", "OPENROUTER_API_KEY"}}
    # Put this interpreter's bin first so aws_execute uses the pinned awscli.
    env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
    script = Path(sys.executable).parent / "ministack-mcp"
    if script.exists():
        return StdioServerParameters(command=str(script), env=env)
    return StdioServerParameters(command=sys.executable, args=["-c", "from ministack_mcp.server import main; main()"], env=env)


def _result_text(result) -> str:
    parts = []
    for c in result.content:
        parts.append(c.text if getattr(c, "type", None) == "text" else json.dumps(c.model_dump(), default=str))
    return "\n".join(parts)


async def run_agent(task: Task, model: str | None = None) -> AgentResult:
    cfg = llm_config(model)
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = RUNS_DIR / task.id / safe_name(cfg["model"]) / f"{ts}.jsonl"
    tr = Transcript(path)
    client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"], max_retries=5, timeout=180)

    turns = tool_calls = blocked = 0
    usage = {"prompt_tokens": 0, "completion_tokens": 0}
    claim, claim_summary, stop_reason = "no_claim", "", "max_turns"
    nudged = False

    with path.with_suffix(".mcp.log").open("w") as errlog:
        async with stdio_client(_mcp_server_params(), errlog=errlog) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                listed = (await session.list_tools()).tools
                exposed = [t for t in listed if task.allows_tool(t.name)]
                tools = [mcp_to_openai(t) for t in exposed] + [FINISH_TOOL]
                exposed_names = {t.name for t in exposed}
                tr.log(
                    "run_start",
                    task=task.id, model=cfg["model"], base_url=cfg["base_url"],
                    max_turns=task.max_turns, max_tool_calls=task.max_tool_calls,
                    mcp_tools_available=sorted(t.name for t in listed),
                    mcp_tools_exposed=sorted(exposed_names),
                )
                messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": task.prompt}]
                for m in messages:
                    tr.log("message", **m)

                try:
                    while turns < task.max_turns:
                        turns += 1
                        t0 = time.monotonic()
                        resp = client.chat.completions.create(model=cfg["model"], messages=messages, tools=tools)
                        if not resp.choices:
                            raise RuntimeError(f"empty response: {resp.model_dump()}")
                        msg = resp.choices[0].message
                        if resp.usage:
                            usage["prompt_tokens"] += resp.usage.prompt_tokens or 0
                            usage["completion_tokens"] += resp.usage.completion_tokens or 0
                        tr.log(
                            "llm_response", turn=turns, latency_s=round(time.monotonic() - t0, 2),
                            content=msg.content, finish_reason=resp.choices[0].finish_reason,
                            tool_calls=[{"id": c.id, "name": c.function.name, "arguments": c.function.arguments} for c in (msg.tool_calls or [])],
                            usage=resp.usage.model_dump() if resp.usage else None,
                        )
                        assistant = {"role": "assistant", "content": msg.content or ""}
                        if msg.tool_calls:
                            assistant["tool_calls"] = [
                                {"id": c.id, "type": "function", "function": {"name": c.function.name, "arguments": c.function.arguments}}
                                for c in msg.tool_calls
                            ]
                        messages.append(assistant)

                        if not msg.tool_calls:
                            if nudged:
                                stop_reason = "no_finish"
                                break
                            nudged = True
                            messages.append({"role": "user", "content": NUDGE})
                            tr.log("message", role="user", content=NUDGE)
                            continue

                        finished = False
                        for call in msg.tool_calls:
                            name = call.function.name
                            try:
                                args = json.loads(call.function.arguments or "{}")
                                if not isinstance(args, dict):
                                    raise ValueError("arguments must be a JSON object")
                            except ValueError as e:
                                output, is_error = f"error: invalid JSON arguments: {e}", True
                                tr.log("tool_call", turn=turns, name=name, arguments=call.function.arguments, result=output, is_error=True)
                            else:
                                if name == "finish":
                                    claim = args.get("status") if args.get("status") in ("done", "failed") else "no_claim"
                                    claim_summary = str(args.get("summary", ""))
                                    output, is_error, finished = "acknowledged", False, True
                                    tr.log("finish", turn=turns, status=args.get("status"), summary=claim_summary)
                                elif name not in exposed_names:
                                    blocked += 1
                                    output, is_error = f"error: tool '{name}' is not available in this task", True
                                    tr.log("tool_call", turn=turns, name=name, arguments=args, result=output, is_error=True, blocked=True)
                                elif tool_calls >= task.max_tool_calls:
                                    output, is_error = "error: tool call budget exhausted", True
                                    tr.log("tool_call", turn=turns, name=name, arguments=args, result=output, is_error=True, over_budget=True)
                                else:
                                    tool_calls += 1
                                    t0 = time.monotonic()
                                    result = await session.call_tool(name, args, read_timeout_seconds=timedelta(seconds=90))
                                    output, is_error = _result_text(result), bool(result.isError)
                                    tr.log("tool_call", turn=turns, n=tool_calls, name=name, arguments=args, result=output,
                                           is_error=is_error, duration_s=round(time.monotonic() - t0, 2))
                            messages.append({"role": "tool", "tool_call_id": call.id, "content": output[:MAX_RESULT_CHARS_TO_MODEL]})
                        if finished:
                            stop_reason = "finished"
                            break
                        if tool_calls >= task.max_tool_calls:
                            stop_reason = "max_tool_calls"
                            break
                except Exception as e:  # noqa: BLE001 - record and still grade whatever state exists
                    stop_reason = f"error: {type(e).__name__}: {e}"
                    tr.log("error", error=stop_reason)

    result = AgentResult(cfg["model"], claim, claim_summary, stop_reason, turns, tool_calls, blocked, usage, str(path))
    tr.log("run_end", **result.to_dict())
    tr.close()
    return result
