"""
Framework adapters for agent-guard.

Each adapter wraps a framework-specific tool/function object so that
agent-guard's authorization check runs transparently before execution.

Available adapters:
  - agent_guard.adapters.langchain  — LangChain BaseTool wrapper
  - agent_guard.adapters.openai     — OpenAI function-calling wrapper
  - agent_guard.adapters.anthropic  — Anthropic tool_use wrapper
"""
