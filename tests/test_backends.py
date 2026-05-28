import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from agent_guard.backends import HttpBackend, StubBackend
from agent_guard.exceptions import BackendError
from agent_guard.types import Action


# ─── StubBackend ────────────────────────────────────────────────────────────

def test_stub_default_allow():
    backend = StubBackend(default="allow")
    action = Action(action_type="read_file")
    assert backend.evaluate(action).allowed


def test_stub_default_block():
    backend = StubBackend(default="block")
    action = Action(action_type="anything")
    assert backend.evaluate(action).blocked


def test_stub_block_pattern():
    backend = StubBackend().block(["delete_*"])
    assert backend.evaluate(Action("delete_user")).blocked
    assert backend.evaluate(Action("read_user")).allowed


def test_stub_escalate_pattern():
    backend = StubBackend().escalate(["send_*"])
    assert backend.evaluate(Action("send_email")).escalated
    assert backend.evaluate(Action("read_email")).allowed


def test_stub_rule_order():
    backend = StubBackend(default="allow")
    backend.block(["send_*"])
    backend.allow(["send_newsletter"])
    # First matching rule wins — "send_newsletter" matches "send_*" (block)
    assert backend.evaluate(Action("send_newsletter")).blocked


def test_stub_chaining():
    backend = (
        StubBackend(default="allow")
        .block(["drop_*"])
        .escalate(["transfer_*"])
    )
    assert backend.evaluate(Action("drop_table")).blocked
    assert backend.evaluate(Action("transfer_funds")).escalated
    assert backend.evaluate(Action("read_record")).allowed


# ─── HttpBackend ─────────────────────────────────────────────────────────────

class _MockHandler(BaseHTTPRequestHandler):
    outcome = "allow"

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        self.rfile.read(length)
        body = json.dumps({"outcome": self.__class__.outcome, "reason": "test"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_):
        pass


def _start_mock_server(outcome="allow"):
    _MockHandler.outcome = outcome
    server = HTTPServer(("127.0.0.1", 0), _MockHandler)
    thread = threading.Thread(target=server.serve_forever)
    thread.daemon = True
    thread.start()
    return server, f"http://127.0.0.1:{server.server_address[1]}"


def test_http_backend_allow():
    server, url = _start_mock_server("allow")
    backend = HttpBackend(url)
    decision = backend.evaluate(Action("any_action"))
    assert decision.allowed
    server.shutdown()


def test_http_backend_block():
    server, url = _start_mock_server("block")
    backend = HttpBackend(url)
    decision = backend.evaluate(Action("any_action"))
    assert decision.blocked
    server.shutdown()


def test_http_backend_unreachable():
    backend = HttpBackend("http://127.0.0.1:1", timeout=1)
    with pytest.raises(BackendError, match="unreachable"):
        backend.evaluate(Action("any_action"))
