"""boto3 access to the environment under test.

MINISTACK_ENDPOINT_URL set   -> every client targets that endpoint (MiniStack).
MINISTACK_ENDPOINT_URL unset -> plain boto3 default credential/endpoint chain (real AWS).
That is the only difference between the two code paths.
"""
from __future__ import annotations

import json
import os
import urllib.request

import boto3


def endpoint_url() -> str | None:
    return os.environ.get("MINISTACK_ENDPOINT_URL") or None


class AwsContext:
    """Client factory shared by setup, reference solutions and graders.

    Records every AWS operation issued so runs can be checked against the
    operations a task declares in task.yaml (and therefore against parity.json).
    """

    def __init__(self) -> None:
        self._session = boto3.session.Session()
        self._clients: dict[str, object] = {}
        self.operations_called: set[tuple[str, str]] = set()
        # Whatever setup.py returned: snapshots of seeded state the grader compares against.
        self.seed: dict = {}

    def client(self, service: str):
        if service not in self._clients:
            client = self._session.client(service, endpoint_url=endpoint_url())
            client.meta.events.register(
                "before-call",
                lambda model, **_: self.operations_called.add((service, model.name)),
            )
            self._clients[service] = client
        return self._clients[service]


def reset_environment() -> dict:
    """Clear all emulator state via MiniStack's reset endpoint (what the
    ministack_reset MCP tool calls). Real AWS cannot be reset, so it is skipped."""
    ep = endpoint_url()
    if ep is None:
        return {"reset": False, "reason": "MINISTACK_ENDPOINT_URL unset (real AWS); nothing reset"}
    req = urllib.request.Request(f"{ep.rstrip('/')}/_ministack/reset", method="POST", data=b"")
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = resp.read().decode() or "{}"
    try:
        detail = json.loads(body)
    except ValueError:
        detail = body
    return {"reset": True, "endpoint": ep, "detail": detail}
