from __future__ import annotations

import json
from typing import Any, Dict, Optional
from urllib.error import URLError
from urllib.request import Request, urlopen

from ..exceptions import BackendError
from ..types import Action, Decision
from .base import Backend

_DEFAULT_BASE_URL = "https://api.xybern.com"


class XybernBackend(Backend):
    """
    Xybern authorisation API backend.

    Routes every action through the Xybern Sentinel control plane.
    Requires an API key from https://xybern.com.

    Example::

        from agent_guard import Guard
        from agent_guard.backends import XybernBackend

        guard = Guard(backend=XybernBackend(api_key="xb_live_..."))
    """

    def __init__(
        self,
        api_key: str,
        workspace_id: Optional[str] = None,
        base_url: str = _DEFAULT_BASE_URL,
        timeout: int = 15,
    ) -> None:
        if not api_key:
            raise ValueError("XybernBackend requires an api_key.")
        self._api_key = api_key
        self._workspace_id = workspace_id
        self._url = f"{base_url.rstrip('/')}/v1/enforce/intercept"
        self._timeout = timeout

    def _headers(self) -> Dict[str, str]:
        h = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._api_key}",
            "X-Agent-Guard": "1",
        }
        if self._workspace_id:
            h["X-Workspace-Id"] = self._workspace_id
        return h

    def evaluate(self, action: Action) -> Decision:
        payload = json.dumps(action.to_dict()).encode()
        req = Request(self._url, data=payload, headers=self._headers(), method="POST")
        try:
            with urlopen(req, timeout=self._timeout) as resp:
                body: Dict[str, Any] = json.loads(resp.read())
        except URLError as exc:
            raise BackendError(f"Xybern API unreachable: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise BackendError(f"Xybern API returned invalid JSON: {exc}") from exc

        if not body.get("ok", True):
            raise BackendError(f"Xybern API error: {body.get('error', 'unknown')}")

        outcome = body.get("decision")
        if outcome not in ("allow", "block", "escalate"):
            raise BackendError(f"Unexpected decision from Xybern: {outcome!r}")

        return Decision(
            outcome=outcome,
            reason=body.get("reasoning", ""),
            decision_id=body.get("decision_id"),
            metadata={
                "trust_score": body.get("trust_score"),
                "vault_entry_id": body.get("vault_entry_id"),
            },
        )
