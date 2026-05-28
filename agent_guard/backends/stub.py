from __future__ import annotations

import fnmatch
from typing import Dict, List

from ..types import Action, Decision, Outcome
from .base import Backend


class StubBackend(Backend):
    """
    In-process backend for local development and testing.

    No external calls — configurable via ``allow``, ``block``, and
    ``escalate`` rules. Pattern-matching supports wildcards (``*``).

    Example::

        stub = StubBackend(default="allow")
        stub.block(["delete_*", "drop_table"])
        stub.escalate(["send_email"])

        guard = Guard(backend=stub)
    """

    def __init__(self, default: Outcome = "allow") -> None:
        self._default: Outcome = default
        self._rules: List[Dict] = []

    # -------------------------------------------------------------------------
    # Rule builders
    # -------------------------------------------------------------------------

    def block(self, patterns: List[str], reason: str = "blocked by policy") -> "StubBackend":
        for p in patterns:
            self._rules.append({"pattern": p, "outcome": "block", "reason": reason})
        return self

    def escalate(self, patterns: List[str], reason: str = "requires human approval") -> "StubBackend":
        for p in patterns:
            self._rules.append({"pattern": p, "outcome": "escalate", "reason": reason})
        return self

    def allow(self, patterns: List[str], reason: str = "explicitly allowed") -> "StubBackend":
        for p in patterns:
            self._rules.append({"pattern": p, "outcome": "allow", "reason": reason})
        return self

    # -------------------------------------------------------------------------
    # Evaluation
    # -------------------------------------------------------------------------

    def evaluate(self, action: Action) -> Decision:
        for rule in self._rules:
            if fnmatch.fnmatch(action.action_type, rule["pattern"]):
                return Decision(outcome=rule["outcome"], reason=rule["reason"])
        return Decision(outcome=self._default, reason="default policy")
