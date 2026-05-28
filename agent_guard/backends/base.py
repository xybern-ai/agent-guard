from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from functools import partial
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..types import Action, Decision


class Backend(ABC):
    """
    Abstract authorization backend.

    Implement ``evaluate`` to plug any authorisation system into agent-guard.
    Async support is provided automatically by running ``evaluate`` in a
    thread-pool executor — override ``evaluate_async`` for native async.
    """

    @abstractmethod
    def evaluate(self, action: "Action") -> "Decision":
        """Synchronously evaluate an action and return a Decision."""

    async def evaluate_async(self, action: "Action") -> "Decision":
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, partial(self.evaluate, action))
