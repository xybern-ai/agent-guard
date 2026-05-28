<p align="center">
  <img src="https://raw.githubusercontent.com/xybern-ai/agent-guard/main/logo.png" alt="Xybern agent-guard" width="120" />
</p>

# xybern-agent-guard

Framework-agnostic authorization middleware for AI agents.

Intercept, inspect, and enforce policies on any agent action before it executes, whether you're using LangChain, OpenAI, Anthropic, or a bare Python function.

> **Get an API key** — email [info@xybern.com](mailto:info@xybern.com) to connect to the Xybern authorisation backend. Free to start.

```python
from agent_guard import Guard
from agent_guard.backends import StubBackend

guard = Guard(backend=StubBackend().block(["delete_*", "drop_table"]))

@guard.intercept("send_email")
def send_email(to, subject, body):
    ...  # only runs if the action is allowed
```

---

## Why

AI agents make real-world calls, they write to databases, send emails, execute trades, call APIs. Without a policy layer between the agent's decision and the actual execution, there's no safety net.

agent-guard sits at that boundary. Every action goes through a `check()` before it runs. The backend decides: `allow`, `block`, or `escalate`. Your code doesn't change, just wrap it.

---

## Get an API key

To use the Xybern authorisation backend in production, email [info@xybern.com](mailto:info@xybern.com) to get an API key. The `StubBackend` works out of the box for local development and testing with no key required.

---

## Install

```bash
pip install xybern-agent-guard
```

No required dependencies. Zero. The core library uses only the Python standard library.

Optional extras for framework adapters:

```bash
pip install xybern-agent-guard[langchain]
pip install xybern-agent-guard[openai]
pip install xybern-agent-guard[anthropic]
pip install xybern-agent-guard[all]
```

---

## Quick start

### Decorator

```python
from agent_guard import Guard
from agent_guard.backends import StubBackend

guard = Guard(backend=StubBackend(default="allow").block(["delete_*"]))

@guard.intercept("write_file")
def write_file(path, content):
    with open(path, "w") as f:
        f.write(content)

@guard.intercept("delete_file")
def delete_file(path):
    os.remove(path)  # never reached — PolicyBlockedError is raised first
```

### Context manager

```python
with guard.protect("database_write", content=query):
    db.execute(query)
```

### Manual check

```python
decision = guard.check("execute_trade", content="Buy 1000 AAPL at market")
if decision.allowed:
    execute_trade(...)
```

### Async

```python
@guard.intercept("send_notification")
async def send_notification(user_id, message):
    await notify(user_id, message)

# or
decision = await guard.check_async("send_notification", content=message)

# or
async with guard.protect_async("write_cache", content=key):
    await cache.set(key, value)
```

---

## Backends

Backends decide what happens when an action is checked. Swap them out without changing application code.

### StubBackend - local, no external calls

```python
from agent_guard.backends import StubBackend

backend = (
    StubBackend(default="allow")           # allow everything by default
    .block(["delete_*", "drop_table"])     # block these patterns
    .escalate(["send_email", "wire_*"])    # escalate these patterns
    .allow(["read_*"])                     # explicitly allow these
)
```

Patterns support wildcards (`*`). Rules are evaluated in order — first match wins.

### HttpBackend — any HTTP endpoint

```python
from agent_guard.backends import HttpBackend

backend = HttpBackend(
    url="https://your-policy-server.com/evaluate",
    headers={"Authorization": "Bearer your-token"},
    timeout=5,
)
```

POST body: serialized `Action`. Expected response: `{"outcome": "allow"|"block"|"escalate", "reason": "..."}`.

### XybernBackend — Xybern Authorisation API

```python
from agent_guard.backends import XybernBackend

backend = XybernBackend(
    api_key="xb_live_...",
    workspace_id="ws_...",   # optional
)
```

Routes every action through the [Xybern](https://xybern.com) Authorisation layer. Gives you audit logs, escalation workflows, policy management UI, and trust scoring out of the box.

### Build your own

```python
from agent_guard.backends import Backend
from agent_guard.types import Action, Decision

class MyBackend(Backend):
    def evaluate(self, action: Action) -> Decision:
        # your logic here
        if action.action_type.startswith("delete"):
            return Decision(outcome="block", reason="deletes are not permitted")
        return Decision(outcome="allow")
```

---

## Framework adapters

### LangChain

```python
from agent_guard.adapters.langchain import guard_tools

tools = guard_tools([search_tool, calculator_tool, email_tool], guard=guard)
agent = create_react_agent(llm, tools, prompt)
```

Or wrap a single tool:

```python
from agent_guard.adapters.langchain import GuardedTool

safe_tool = GuardedTool.wrap(email_tool, guard=guard, action_type="send_email")
```

### OpenAI

```python
from agent_guard.adapters.openai import dispatch_tool_calls

response = client.chat.completions.create(model="gpt-4o", messages=messages, tools=tools)

tool_results = dispatch_tool_calls(
    response.choices[0].message.tool_calls,
    handlers={"get_weather": get_weather, "send_email": send_email},
    guard=guard,
)
```

### Anthropic

```python
from agent_guard.adapters.anthropic import dispatch_tool_use

response = client.messages.create(model="claude-opus-4-7", messages=messages, tools=tools)

tool_results = dispatch_tool_use(
    response.content,
    handlers={"web_search": search, "send_email": send_email},
    guard=guard,
)
```

---

## Configuration

```python
Guard(
    backend=...,
    on_block="raise",     # "raise" (default) | "log" | "ignore"
    on_escalate="raise",  # "raise" (default) | "log" | "ignore"
    agent_id="my-agent",  # passed to the backend with every action
)
```

| `on_block` / `on_escalate` | behaviour |
|---|---|
| `"raise"` | raises `PolicyBlockedError` / `PolicyEscalatedError` |
| `"log"` | logs a warning, returns the Decision, execution continues |
| `"ignore"` | silently returns the Decision, execution continues |

---

## Exceptions

```python
from agent_guard import PolicyBlockedError, PolicyEscalatedError, BackendError

try:
    result = execute_trade(symbol="AAPL", qty=1000)
except PolicyBlockedError as e:
    print(e.action.action_type)   # "execute_trade"
    print(e.decision.reason)      # reason from the backend
except PolicyEscalatedError as e:
    notify_human_reviewer(e.action, e.decision)
except BackendError as e:
    # backend unreachable or returned unexpected response
    log_and_fail_safe(e)
```

---

## Running tests

```bash
pip install -e ".[dev]"
pytest
```

---

## Contributing

PRs welcome. Open an issue first for anything beyond small fixes.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Links

- [Documentation](https://docs.xybern.com/agent-guard/quick-start)
- [Changelog](https://docs.xybern.com/changelog)
- [Xybern](https://xybern.com)

---

Built by [Xybern](https://xybern.com) — regulated AI infrastructure.
