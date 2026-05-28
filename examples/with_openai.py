"""
agent-guard + OpenAI tool calls.

Requires: pip install xybern-agent-guard[openai]
"""
import json
import os

from agent_guard import Guard
from agent_guard.backends import StubBackend
from agent_guard.adapters.openai import dispatch_tool_calls

import openai

client = openai.OpenAI(api_key=os.environ["OPENAI_API_KEY"])

guard = Guard(
    backend=StubBackend(default="allow").block(["send_email"]),
    agent_id="openai-demo-agent",
)

tools = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get current weather for a city",
            "parameters": {
                "type": "object",
                "properties": {"city": {"type": "string"}},
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Send an email",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"},
                },
                "required": ["to", "subject", "body"],
            },
        },
    },
]


def get_weather(city: str) -> dict:
    return {"city": city, "temperature": "22°C", "condition": "sunny"}


def send_email(to: str, subject: str, body: str) -> dict:
    print(f"Sending email to {to}...")
    return {"sent": True}


handlers = {"get_weather": get_weather, "send_email": send_email}

messages = [{"role": "user", "content": "What's the weather in London? Also email me the result at test@example.com"}]

response = client.chat.completions.create(model="gpt-4o", messages=messages, tools=tools)
msg = response.choices[0].message

if msg.tool_calls:
    # agent-guard checks each tool call before dispatching to local handler
    tool_results = dispatch_tool_calls(msg.tool_calls, handlers=handlers, guard=guard)
    print("Tool results:", json.dumps(tool_results, indent=2))
