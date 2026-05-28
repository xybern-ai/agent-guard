from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import Action, Decision


class AgentGuardError(Exception):
    """Base exception for agent-guard."""


class PolicyBlockedError(AgentGuardError):
    """Raised when an action is blocked by policy."""

    def __init__(self, action: "Action", decision: "Decision") -> None:
        self.action = action
        self.decision = decision
        super().__init__(
            f"Action '{action.action_type}' blocked: {decision.reason or 'policy violation'}"
        )


class PolicyEscalatedError(AgentGuardError):
    """Raised when an action requires human approval before proceeding."""

    def __init__(self, action: "Action", decision: "Decision") -> None:
        self.action = action
        self.decision = decision
        super().__init__(
            f"Action '{action.action_type}' requires escalation: {decision.reason or 'human approval required'}"
        )


class BackendError(AgentGuardError):
    """Raised when the authorization backend returns an error or is unreachable."""
