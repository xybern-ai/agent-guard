"""
Anthropic adapter for agent-guard.

Intercepts tool_use blocks from Claude responses before dispatching
to local handlers.

Requires: ``pip install xybern-agent-guard[anthropic]``
"""
from __future__ import annotations

import asyncio
import importlib.util
import json
from typing import Any, Callable, Dict, List

from ..guard import Guard

if importlib.util.find_spec("anthropic") is None:  # pragma: no cover
    raise ImportError("anthropic is not installed. Run: pip install xybern-agent-guard[anthropic]")


def dispatch_tool_use(
    content_blocks: List[Any],
    handlers: Dict[str, Callable[..., Any]],
    guard: Guard,
) -> List[Dict[str, Any]]:
    """
    Dispatch Claude ``tool_use`` content blocks through agent-guard, then
    call the matching handler for each one.

    Returns a list of ``tool_result`` blocks ready to pass back to Claude.

    Example::

        tool_results = dispatch_tool_use(
            response.content,
            handlers={"web_search": search, "send_email": send_email},
            guard=guard,
        )
        messages.append({"role": "user", "content": tool_results})
    """
    results = []
    for block in content_blocks:
        if block.type != "tool_use":
            continue

        handler = handlers.get(block.name)
        if handler is None:
            raise ValueError(f"No handler registered for tool '{block.name}'")

        content_str = json.dumps(block.input) if block.input else ""
        guard.check(block.name, content=content_str)

        output = handler(**block.input)
        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": json.dumps(output) if not isinstance(output, str) else output,
        })
    return results


async def dispatch_tool_use_async(
    content_blocks: List[Any],
    handlers: Dict[str, Callable[..., Any]],
    guard: Guard,
) -> List[Dict[str, Any]]:
    """Async version of ``dispatch_tool_use``."""
    results = []
    for block in content_blocks:
        if block.type != "tool_use":
            continue

        handler = handlers.get(block.name)
        if handler is None:
            raise ValueError(f"No handler registered for tool '{block.name}'")

        content_str = json.dumps(block.input) if block.input else ""
        await guard.check_async(block.name, content=content_str)

        if asyncio.iscoroutinefunction(handler):
            output = await handler(**block.input)
        else:
            output = handler(**block.input)

        results.append({
            "type": "tool_result",
            "tool_use_id": block.id,
            "content": json.dumps(output) if not isinstance(output, str) else output,
        })
    return results
