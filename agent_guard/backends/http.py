from __future__ import annotations

import json
from typing import Any, Dict, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from ..exceptions import BackendError
from ..types import Action, Decision
from .base import Backend


class HttpBackend(Backend):
    """
    Generic HTTP backend.

    POSTs the serialized Action to any endpoint that returns a JSON body
    with an ``outcome`` field (``"allow"`` | ``"block"`` | ``"escalate"``).

    Request body::

        {
          "action_type": "...",
          "content": "...",
          "metadata": {...},
          "agent_id": "...",
          "timestamp": "..."
        }

    Expected response::

        {
          "outcome": "allow" | "block" | "escalate",
          "reason": "...",          // optional
          "decision_id": "...",     // optional
          "metadata": {...}         // optional
        }
    """

    def __init__(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 10,
    ) -> None:
        self.url = url
        self.headers: Dict[str, str] = {"Content-Type": "application/json"}
        if headers:
            self.headers.update(headers)
        self.timeout = timeout

    def evaluate(self, action: Action) -> Decision:
        payload = json.dumps(action.to_dict()).encode()
        req = Request(self.url, data=payload, headers=self.headers, method="POST")
        try:
            with urlopen(req, timeout=self.timeout) as resp:
                body: Dict[str, Any] = json.loads(resp.read())
        except URLError as exc:
            raise BackendError(f"Backend unreachable: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise BackendError(f"Backend returned invalid JSON: {exc}") from exc

        outcome = body.get("outcome")
        if outcome not in ("allow", "block", "escalate"):
            raise BackendError(
                f"Backend returned unexpected outcome: {outcome!r}. "
                "Expected 'allow', 'block', or 'escalate'."
            )
        return Decision(
            outcome=outcome,
            reason=body.get("reason", ""),
            decision_id=body.get("decision_id"),
            metadata=body.get("metadata", {}),
        )
