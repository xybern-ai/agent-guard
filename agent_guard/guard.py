from __future__ import annotations

import asyncio
import functools
import logging
from contextlib import contextmanager, asynccontextmanager
from typing import Any, Callable, Dict, Literal, Optional, TypeVar

from .backends.base import Backend
from .backends.stub import StubBackend
from .exceptions import PolicyBlockedError, PolicyEscalatedError
from .types import Action, Decision

logger = logging.getLogger("agent_guard")

F = TypeVar("F", bound=Callable[..., Any])

OnBlock = Literal["raise", "log", "ignore"]


class Guard:
    """
    Authorization middleware for AI agent actions.

    Every action passes through ``check()`` before execution. The backend
    decides: ``allow``, ``block``, or ``escalate``.

    Usage::

        from agent_guard import Guard
        from agent_guard.backends import StubBackend

        guard = Guard(backend=StubBackend().block(["delete_*"]))

        # Decorator
        @guard.intercept("send_email")
        def send_email(to, subject, body):
            ...

        # Context manager
        with guard.protect("database_write", content="DROP TABLE users"):
            db.execute(...)

        # Manual check
        decision = guard.check("execute_trade", content="Buy 1000 shares")
        if decision.allowed:
            execute_trade()
    """

    def __init__(
        self,
        backend: Optional[Backend] = None,
        on_block: OnBlock = "raise",
        on_escalate: OnBlock = "raise",
        agent_id: Optional[str] = None,
    ) -> None:
        self._backend: Backend = backend or StubBackend(default="allow")
        self._on_block: OnBlock = on_block
        self._on_escalate: OnBlock = on_escalate
        self._agent_id: Optional[str] = agent_id

    # -------------------------------------------------------------------------
    # Core evaluation
    # -------------------------------------------------------------------------

    def check(
        self,
        action_type: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
    ) -> Decision:
        """Evaluate an action synchronously and return a Decision."""
        action = Action(
            action_type=action_type,
            content=content,
            metadata=metadata,
            agent_id=agent_id or self._agent_id,
        )
        decision = self._backend.evaluate(action)
        self._handle(action, decision)
        return decision

    async def check_async(
        self,
        action_type: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        agent_id: Optional[str] = None,
    ) -> Decision:
        """Evaluate an action asynchronously and return a Decision."""
        action = Action(
            action_type=action_type,
            content=content,
            metadata=metadata,
            agent_id=agent_id or self._agent_id,
        )
        decision = await self._backend.evaluate_async(action)
        self._handle(action, decision)
        return decision

    # -------------------------------------------------------------------------
    # Decorator
    # -------------------------------------------------------------------------

    def intercept(
        self,
        action_type: Optional[str] = None,
        content_arg: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Callable[[F], F]:
        """
        Decorator that checks the action before calling the wrapped function.

        ``action_type`` defaults to the function name if not provided.
        ``content_arg`` is the name of the function argument to use as content.

        Example::

            @guard.intercept("send_email", content_arg="body")
            def send_email(to, subject, body):
                ...
        """
        def decorator(fn: F) -> F:
            _action_type = action_type or fn.__name__

            if asyncio.iscoroutinefunction(fn):
                @functools.wraps(fn)
                async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
                    content = kwargs.get(content_arg) if content_arg else None
                    await self.check_async(_action_type, content=content, metadata=metadata)
                    return await fn(*args, **kwargs)
                return async_wrapper  # type: ignore[return-value]

            @functools.wraps(fn)
            def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
                content = kwargs.get(content_arg) if content_arg else None
                self.check(_action_type, content=content, metadata=metadata)
                return fn(*args, **kwargs)
            return sync_wrapper  # type: ignore[return-value]

        return decorator

    # -------------------------------------------------------------------------
    # Context managers
    # -------------------------------------------------------------------------

    @contextmanager
    def protect(
        self,
        action_type: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Synchronous context manager. Checks the action before entering the block.

        Example::

            with guard.protect("database_write", content=query):
                db.execute(query)
        """
        self.check(action_type, content=content, metadata=metadata)
        yield

    @asynccontextmanager
    async def protect_async(
        self,
        action_type: str,
        content: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Async context manager version of ``protect``."""
        await self.check_async(action_type, content=content, metadata=metadata)
        yield

    # -------------------------------------------------------------------------
    # Internal
    # -------------------------------------------------------------------------

    def _handle(self, action: Action, decision: Decision) -> None:
        if decision.blocked:
            self._apply_policy(action, decision, "block", self._on_block, PolicyBlockedError)
        elif decision.escalated:
            self._apply_policy(action, decision, "escalate", self._on_escalate, PolicyEscalatedError)
        else:
            logger.debug("Allowed: %s", action.action_type)

    def _apply_policy(self, action, decision, label, mode, exc_cls):
        if mode == "raise":
            raise exc_cls(action, decision)
        elif mode == "log":
            logger.warning(
                "Action %r %sd by policy: %s",
                action.action_type, label, decision.reason,
            )
        # "ignore" — do nothing
