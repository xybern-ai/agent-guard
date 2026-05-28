"""
OpenAI adapter for agent-guard.

Intercepts function/tool calls before the local handler executes them.
Works with both the legacy ``function_call`` API and the newer ``tool_calls`` API.

Requires: ``pip install xybern-agent-guard[openai]``
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Optional

import importlib.util

from ..guard import Guard

if importlib.util.find_spec("openai") is None:  # pragma: no cover
    raise ImportError("openai is not installed. Run: pip install xybern-agent-guard[openai]")


def guard_tool_call(
    tool_name: str,
    arguments: str,
    handler: Callable[..., Any],
    guard: Guard,
    action_type: Optional[str] = None,
) -> Any:
    """
    Check a single tool call, then invoke its handler.

    ``arguments`` is the raw JSON string from the OpenAI response.

    Example::

        result = guard_tool_call(
            tool_name="send_email",
            arguments=tool_call.function.arguments,
            handler=send_email,
            guard=guard,
        )
    """
    _action_type = action_type or tool_name
    guard.check(_action_type, content=arguments)
    kwargs = json.loads(arguments) if arguments else {}
    return handler(**kwargs)


async def guard_tool_call_async(
    tool_name: str,
    arguments: str,
    handler: Callable[..., Any],
    guard: Guard,
    action_type: Optional[str] = None,
) -> Any:
    """Async version of ``guard_tool_call``."""
    _action_type = action_type or tool_name
    await guard.check_async(_action_type, content=arguments)
    kwargs = json.loads(arguments) if arguments else {}
    if hasattr(handler, "__await__") or hasattr(handler, "__aiter__"):
        return await handler(**kwargs)
    return handler(**kwargs)


def dispatch_tool_calls(
    tool_calls: List[Any],
    handlers: Dict[str, Callable[..., Any]],
    guard: Guard,
) -> List[Dict[str, Any]]:
    """
    Dispatch a list of OpenAI ``tool_calls`` through agent-guard, then
    call the matching handler for each one.

    Returns a list of ``{tool_call_id, role, content}`` dicts ready to
    append to the messages list.

    Example::

        messages += dispatch_tool_calls(
            response.choices[0].message.tool_calls,
            handlers={"send_email": send_email, "search": search},
            guard=guard,
        )
    """
    results = []
    for tc in tool_calls:
        name = tc.function.name
        handler = handlers.get(name)
        if handler is None:
            raise ValueError(f"No handler registered for tool '{name}'")
        output = guard_tool_call(name, tc.function.arguments, handler, guard)
        results.append({
            "tool_call_id": tc.id,
            "role": "tool",
            "content": json.dumps(output) if not isinstance(output, str) else output,
        })
    return results
