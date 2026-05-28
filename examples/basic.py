"""
Basic agent-guard usage — no external dependencies required.
"""
from agent_guard import Guard, PolicyBlockedError
from agent_guard.backends import StubBackend

# Build a guard with a local stub backend
backend = (
    StubBackend(default="allow")
    .block(["delete_*", "drop_table", "rm_rf"])
    .escalate(["send_email", "transfer_funds"])
)
guard = Guard(backend=backend, agent_id="demo-agent")


# ── 1. Decorator ─────────────────────────────────────────────────────────────

@guard.intercept("read_file")
def read_file(path: str) -> str:
    return f"<contents of {path}>"


@guard.intercept("delete_file")
def delete_file(path: str) -> None:
    print(f"Deleted {path}")


# ── 2. Context manager ───────────────────────────────────────────────────────

def write_record(record: dict) -> None:
    with guard.protect("write_db", content=str(record)):
        print(f"Wrote record: {record}")


# ── 3. Manual check ──────────────────────────────────────────────────────────

def maybe_execute(action_type: str, content: str) -> None:
    decision = guard.check(action_type, content=content)
    if decision.allowed:
        print(f"[ALLOWED] {action_type}")
    # blocked/escalated would raise before we get here (default on_block="raise")


if __name__ == "__main__":
    print(read_file("/etc/hosts"))

    write_record({"id": 1, "name": "Alice"})

    try:
        delete_file("/important/file.txt")
    except PolicyBlockedError as e:
        print(f"[BLOCKED] {e}")

    maybe_execute("read_logs", content="last 100 lines")
