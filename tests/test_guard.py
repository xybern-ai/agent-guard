import pytest
from agent_guard import Guard, PolicyBlockedError, PolicyEscalatedError
from agent_guard.backends import StubBackend


@pytest.fixture
def allow_guard():
    return Guard(backend=StubBackend(default="allow"))


@pytest.fixture
def block_guard():
    return Guard(backend=StubBackend(default="block"))


@pytest.fixture
def selective_guard():
    backend = StubBackend(default="allow")
    backend.block(["delete_*", "drop_table"])
    backend.escalate(["send_email"])
    return Guard(backend=backend)


# ─── check() ────────────────────────────────────────────────────────────────

def test_check_allow(allow_guard):
    decision = allow_guard.check("read_file")
    assert decision.allowed


def test_check_block_raises(block_guard):
    with pytest.raises(PolicyBlockedError) as exc_info:
        block_guard.check("any_action")
    assert "any_action" in str(exc_info.value)


def test_check_escalate_raises(selective_guard):
    with pytest.raises(PolicyEscalatedError):
        selective_guard.check("send_email")


def test_selective_block(selective_guard):
    with pytest.raises(PolicyBlockedError):
        selective_guard.check("delete_user")

    decision = selective_guard.check("read_user")
    assert decision.allowed


def test_wildcard_matching(selective_guard):
    with pytest.raises(PolicyBlockedError):
        selective_guard.check("delete_everything")


# ─── on_block modes ─────────────────────────────────────────────────────────

def test_on_block_log(caplog):
    guard = Guard(backend=StubBackend(default="block"), on_block="log")
    import logging
    with caplog.at_level(logging.WARNING, logger="agent_guard"):
        decision = guard.check("risky_action")
    assert decision.blocked
    assert "risky_action" in caplog.text


def test_on_block_ignore():
    guard = Guard(backend=StubBackend(default="block"), on_block="ignore")
    decision = guard.check("risky_action")
    assert decision.blocked


# ─── decorator ──────────────────────────────────────────────────────────────

def test_decorator_allow(allow_guard):
    @allow_guard.intercept("read_file")
    def read_file(path):
        return f"contents of {path}"

    assert read_file("/etc/hosts") == "contents of /etc/hosts"


def test_decorator_block(block_guard):
    @block_guard.intercept("delete_file")
    def delete_file(path):
        return "deleted"

    with pytest.raises(PolicyBlockedError):
        delete_file("/etc/hosts")


def test_decorator_uses_function_name(allow_guard):
    calls = []

    @allow_guard.intercept()
    def my_action():
        calls.append(1)

    my_action()
    assert calls == [1]


# ─── context manager ────────────────────────────────────────────────────────

def test_protect_allow(allow_guard):
    executed = []
    with allow_guard.protect("read_db"):
        executed.append(1)
    assert executed == [1]


def test_protect_block(block_guard):
    executed = []
    with pytest.raises(PolicyBlockedError):
        with block_guard.protect("write_db"):
            executed.append(1)
    assert executed == []


# ─── async ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_check_async_allow(allow_guard):
    decision = await allow_guard.check_async("read_file")
    assert decision.allowed


@pytest.mark.asyncio
async def test_check_async_block(block_guard):
    with pytest.raises(PolicyBlockedError):
        await block_guard.check_async("write_file")


@pytest.mark.asyncio
async def test_async_decorator(allow_guard):
    @allow_guard.intercept("async_action")
    async def async_fn():
        return "ok"

    result = await async_fn()
    assert result == "ok"


@pytest.mark.asyncio
async def test_protect_async(allow_guard):
    executed = []
    async with allow_guard.protect_async("safe_action"):
        executed.append(1)
    assert executed == [1]
