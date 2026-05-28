"""
agent-guard + Xybern authorisation backend.

Every action is evaluated by the Xybern Sentinel control plane.
Get an API key at https://xybern.com/contact

Requires: pip install xybern-agent-guard
"""
import os
from agent_guard import Guard, PolicyBlockedError, PolicyEscalatedError
from agent_guard.backends import XybernBackend

guard = Guard(
    backend=XybernBackend(
        api_key=os.environ["XYBERN_API_KEY"],
        workspace_id=os.environ.get("XYBERN_WORKSPACE_ID"),
    ),
    agent_id="my-production-agent",
)


@guard.intercept("execute_trade")
def execute_trade(symbol: str, quantity: int, side: str) -> dict:
    print(f"Executing trade: {side} {quantity} {symbol}")
    return {"order_id": "ORD-001", "status": "filled"}


@guard.intercept("send_wire_transfer")
def send_wire_transfer(amount: float, account: str) -> dict:
    print(f"Wiring ${amount} to {account}")
    return {"tx_id": "TXN-001"}


if __name__ == "__main__":
    try:
        result = execute_trade("AAPL", 100, "buy")
        print("Trade executed:", result)
    except PolicyBlockedError as e:
        print(f"Trade blocked by policy: {e}")
    except PolicyEscalatedError as e:
        print(f"Trade requires human approval: {e}")
