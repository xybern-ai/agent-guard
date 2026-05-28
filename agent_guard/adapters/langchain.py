"""
LangChain adapter for agent-guard.

Requires: ``pip install xybern-agent-guard[langchain]``
"""
from __future__ import annotations

from typing import Any, Optional

from ..guard import Guard

try:
    from langchain.tools import BaseTool
    from langchain_core.callbacks import CallbackManagerForToolRun
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "LangChain is not installed. Run: pip install xybern-agent-guard[langchain]"
    ) from exc


class GuardedTool(BaseTool):
    """
    Wraps any LangChain ``BaseTool`` with agent-guard authorization.

    The guard check runs in ``_run`` / ``_arun`` before the underlying
    tool executes. A blocked action raises ``PolicyBlockedError`` (which
    LangChain treats as a tool error).

    Example::

        from langchain_community.tools import WikipediaQueryRun
        from agent_guard import Guard
        from agent_guard.adapters.langchain import GuardedTool

        base_tool = WikipediaQueryRun(...)
        tool = GuardedTool.wrap(base_tool, guard=guard, action_type="web_search")
    """

    _inner: BaseTool
    _guard: Guard
    _action_type: str

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def wrap(
        cls,
        tool: BaseTool,
        guard: Guard,
        action_type: Optional[str] = None,
    ) -> "GuardedTool":
        obj = cls(
            name=tool.name,
            description=tool.description,
        )
        obj._inner = tool
        obj._guard = guard
        obj._action_type = action_type or tool.name
        return obj

    def _run(
        self,
        tool_input: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Any:
        self._guard.check(self._action_type, content=tool_input)
        return self._inner._run(tool_input, run_manager=run_manager)

    async def _arun(
        self,
        tool_input: str,
        run_manager: Optional[CallbackManagerForToolRun] = None,
    ) -> Any:
        await self._guard.check_async(self._action_type, content=tool_input)
        return await self._inner._arun(tool_input, run_manager=run_manager)


def guard_tools(tools: list, guard: Guard) -> list:
    """Wrap a list of LangChain tools with agent-guard. Action type = tool name."""
    return [GuardedTool.wrap(t, guard=guard) for t in tools]
