"""Static IAM-style policy analysis for graders.

MiniStack stores bucket, queue and IAM policies but does not evaluate them, so
graders reason about the documents the way real AWS would. This is deliberately
a small, conservative subset of IAM semantics: anything it does not understand
(e.g. an unsupported condition operator) is treated as "does not grant".
"""
from __future__ import annotations

import json
import re
import urllib.parse
from dataclasses import dataclass, field


class PolicyError(ValueError):
    pass


def as_list(x) -> list:
    if x is None:
        return []
    return list(x) if isinstance(x, (list, tuple)) else [x]


def parse_policy(doc) -> dict:
    """Accept a dict, a JSON string, or IAM's URL-encoded JSON string."""
    if isinstance(doc, dict):
        return doc
    if not isinstance(doc, str):
        raise PolicyError(f"policy is {type(doc).__name__}, not a document")
    for candidate in (doc, urllib.parse.unquote(doc)):
        try:
            parsed = json.loads(candidate)
        except ValueError:
            continue
        if isinstance(parsed, dict):
            return parsed
    raise PolicyError(f"policy is not valid JSON: {doc[:80]!r}")


def statements(policy: dict) -> list[dict]:
    return [s for s in as_list(policy.get("Statement")) if isinstance(s, dict)]


def _pattern(p: str) -> re.Pattern:
    return re.compile("^" + re.escape(p).replace(r"\*", ".*").replace(r"\?", ".") + "$", re.DOTALL)


def action_matches(pattern: str, action: str) -> bool:
    return bool(_pattern(pattern.lower()).match(action.lower()))  # IAM actions are case-insensitive


def resource_matches(pattern: str, arn: str) -> bool:
    return bool(_pattern(pattern).match(arn))


def has_wildcard(s: str) -> bool:
    return "*" in s or "?" in s


def principals(stmt: dict) -> set[tuple[str, str]]:
    """{('*','*')} for everyone, else {(type, value)} e.g. ('Service', 'sns.amazonaws.com')."""
    p = stmt.get("Principal")
    if p is None:
        return set()
    if p == "*":
        return {("*", "*")}
    out = set()
    for kind, values in p.items():
        for v in as_list(values):
            out.add(("*", "*") if (kind == "AWS" and v == "*") else (kind, v))
    return out


def _norm_condition(cond) -> dict:
    out = {}
    for op, kv in (cond or {}).items():
        out[op.lower()] = {k.lower(): sorted(str(v).lower() for v in as_list(vals)) for k, vals in kv.items()}
    return out


def normalize(stmt: dict) -> dict:
    """Comparable form of a statement; Sid is ignored."""
    return {
        "Effect": stmt.get("Effect"),
        "Principal": sorted(principals(stmt)),
        "Action": sorted(a.lower() for a in as_list(stmt.get("Action"))),
        "NotAction": sorted(a.lower() for a in as_list(stmt.get("NotAction"))),
        "Resource": sorted(as_list(stmt.get("Resource"))),
        "NotResource": sorted(as_list(stmt.get("NotResource"))),
        "Condition": _norm_condition(stmt.get("Condition")),
    }


def equivalent(a: dict, b: dict) -> bool:
    return normalize(a) == normalize(b)


def describe(stmt: dict) -> str:
    keys = ("Effect", "Principal", "Action", "NotAction", "Resource", "NotResource", "Condition")
    return json.dumps({k: stmt[k] for k in keys if k in stmt}, sort_keys=True)


# ---------------------------------------------------------------- resource policies


def _condition_allows(cond: dict, context: dict[str, str]) -> tuple[bool, str]:
    """Evaluate the condition operators a delivery policy normally uses."""
    for op, kv in (cond or {}).items():
        for key, vals in kv.items():
            actual = context.get(key.lower())
            if actual is None:
                return False, f"condition key {key} not supported by the grader"
            if op in ("ArnEquals", "StringEquals"):
                ok = actual in as_list(vals)
            elif op in ("ArnLike", "StringLike"):
                ok = any(resource_matches(v, actual) for v in as_list(vals))
            else:
                return False, f"condition operator {op} not supported by the grader"
            if not ok:
                return False, f"{op} {key}={as_list(vals)} does not match {actual}"
    return True, ""


def has_source_arn_condition(stmt: dict) -> bool:
    return any(k.lower() == "aws:sourcearn" for kv in (stmt.get("Condition") or {}).values() for k in kv)


def service_can_send(policy_doc, *, service: str, action: str, resource_arn: str, source_arn: str,
                     require_source_arn: bool) -> tuple[bool, str]:
    """Would real AWS let `service` (acting for `source_arn`) perform `action` on
    `resource_arn` under this resource policy? Returns (allowed, explanation)."""
    if not policy_doc:
        return False, "no policy"
    try:
        policy = parse_policy(policy_doc)
    except PolicyError as e:
        return False, str(e)
    account = source_arn.split(":")[4] if source_arn.count(":") >= 5 else ""
    context = {"aws:sourcearn": source_arn, "aws:sourceaccount": account}
    applicable = [
        s for s in statements(policy)
        if {("*", "*"), ("Service", service)} & principals(s)
        and any(action_matches(a, action) for a in as_list(s.get("Action")))
        and any(resource_matches(r, resource_arn) for r in as_list(s.get("Resource")))
    ]
    # Explicit Deny wins regardless of statement order.
    for s in applicable:
        if s.get("Effect") == "Deny" and _condition_allows(s.get("Condition"), context)[0]:
            return False, f"explicit Deny: {describe(s)}"
    reasons = []
    for s in applicable:
        if s.get("Effect") != "Allow":
            continue
        if require_source_arn and not has_source_arn_condition(s):
            reasons.append(f"Allow without aws:SourceArn condition: {describe(s)}")
            continue
        ok, why = _condition_allows(s.get("Condition"), context)
        if ok:
            return True, f"allowed by {describe(s)}"
        reasons.append(why)
    return False, "; ".join(reasons) or f"no Allow statement for {service} -> {action} on {resource_arn}"


# ---------------------------------------------------------------- identity policies


@dataclass
class Grant:
    action: str
    resource: str
    condition: dict = field(default_factory=dict)
    source: str = ""

    def __str__(self) -> str:
        cond = f" if {json.dumps(self.condition, sort_keys=True)}" if self.condition else ""
        return f"{self.action} on {self.resource}{cond} [{self.source}]"


def allow_grants(docs: list[tuple[str, dict]]) -> tuple[list[Grant], list[str]]:
    """Flatten Allow statements of (source_name, document) pairs into (action, resource)
    grants. NotAction / NotResource in an Allow are returned as violations: they grant
    everything except a list, which is never least privilege."""
    grants, violations = [], []
    for source, doc in docs:
        for s in statements(doc):
            if s.get("Effect") != "Allow":
                continue
            if "NotAction" in s or "NotResource" in s:
                violations.append(f"Allow with NotAction/NotResource [{source}]: {describe(s)}")
                continue
            for a in as_list(s.get("Action")):
                for r in as_list(s.get("Resource")):
                    grants.append(Grant(a, r, s.get("Condition") or {}, source))
    return grants, violations


def covers(grants: list[Grant], action: str, resource: str) -> bool:
    return any(action_matches(g.action, action) and resource_matches(g.resource, resource) for g in grants)


@dataclass
class Permitted:
    """One shape of grant the task considers necessary (or an accepted standard extra)."""
    actions: set[str]                      # lower-case, no wildcards
    resource_ok: callable                  # resource string -> bool
    condition_ok: callable = lambda c: True  # condition dict -> bool (conditions only narrow)

    def allows(self, g: Grant) -> bool:
        return (not has_wildcard(g.action) and g.action.lower() in self.actions
                and self.resource_ok(g.resource) and self.condition_ok(g.condition))


def excess_grants(grants: list[Grant], permitted: list[Permitted]) -> list[Grant]:
    return [g for g in grants if not any(p.allows(g) for p in permitted)]
