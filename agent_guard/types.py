from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Literal, Optional


Outcome = Literal["allow", "block", "escalate"]


@dataclass
class Action:
    action_type: str
    content: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    agent_id: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "action_type": self.action_type,
            "content": self.content,
            "metadata": self.metadata or {},
            "agent_id": self.agent_id,
            "timestamp": self.timestamp,
        }


@dataclass
class Decision:
    outcome: Outcome
    reason: str = ""
    decision_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def allowed(self) -> bool:
        return self.outcome == "allow"

    @property
    def blocked(self) -> bool:
        return self.outcome == "block"

    @property
    def escalated(self) -> bool:
        return self.outcome == "escalate"

    def __repr__(self) -> str:
        return f"Decision(outcome={self.outcome!r}, reason={self.reason!r})"
