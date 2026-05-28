"""
agent-guard — Framework-agnostic authorization middleware for AI agents.

Quick start::

    from agent_guard import Guard
    from agent_guard.backends import StubBackend

    guard = Guard(backend=StubBackend().block(["delete_*", "drop_table"]))

    @guard.intercept("send_email")
    def send_email(to, subject, body):
        ...
"""

from .exceptions import AgentGuardError, BackendError, PolicyBlockedError, PolicyEscalatedError
from .guard import Guard
from .types import Action, Decision

__version__ = "0.1.4"
__all__ = [
    "Guard",
    "Action",
    "Decision",
    "AgentGuardError",
    "PolicyBlockedError",
    "PolicyEscalatedError",
    "BackendError",
]
