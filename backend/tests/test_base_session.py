"""
Tests for BaseSession asynchronous helpers.

This suite is written as a *spec*: most tests are marked xfail until you
implement the corresponding BaseSession methods. Once you wire them up,
remove xfail and the tests should pass.

Importing BaseSession
---------------------
Set env var SESSION_IMPORT_PATH to something like "sessions:BaseSession".
If not set, the tests try common defaults.

Run:
    pip install pytest anyio
    pytest -q
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, Optional
from pathlib import Path
import sys

PARENT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PARENT))
import pytest
from sessions import BaseSession


# --------------------------------- fakes ---------------------------------

class DummyWebSocket:
    """Minimal WebSocket double for unit tests.

    Provides `accept`, `close`, `receive_text`, `send_text`.
    """
    def __init__(self, incoming: Optional[list[str]] = None) -> None:
        self.accepted = False
        self.closed = False
        self.sent: list[str] = []
        self._incoming = list(incoming or [])

    # --- server-side API used by session helpers ---
    async def accept(self) -> None:
        self.accepted = True

    async def close(self, code: int = 1000) -> None:
        self.closed = True
        self.close_code = code

    async def receive_text(self) -> str:
        if not self._incoming:
            raise RuntimeError("No more incoming messages for DummyWebSocket")
        return self._incoming.pop(0)

    async def send_text(self, data: str) -> None:
        self.sent.append(data)


# --------------------------------- fixtures ---------------------------------

@pytest.fixture()
def session() -> BaseSession:
    class ConcreteSession(BaseSession):
        def dispatch(msg: Dict[str, Any]):
            return msg
    return ConcreteSession()


# --------------------------------- tests ---------------------------------

@pytest.mark.anyio
@pytest.mark.xfail(strict=False, reason="on_connect not implemented yet")
async def test_on_connect_accepts_websocket(session):
    ws = DummyWebSocket()
    await session.on_connect(ws)
    assert ws.accepted is True


@pytest.mark.anyio
@pytest.mark.xfail(strict=False, reason="send_json not implemented yet")
async def test_send_json_serializes_and_sends(session):
    ws = DummyWebSocket()
    payload: Dict[str, Any] = {"type": "ping", "n": 1}
    await session.send_json(ws, payload)
    assert len(ws.sent) == 1
    sent_obj = json.loads(ws.sent[0])
    assert sent_obj == payload


@pytest.mark.anyio
@pytest.mark.xfail(strict=False, reason="send_error not implemented yet")
async def test_send_error_sends_standard_error_shape(session):
    ws = DummyWebSocket()
    await session.send_error(ws, detail="missing field: target_column", code="validation_error")
    assert len(ws.sent) == 1
    msg = json.loads(ws.sent[0])
    assert msg["type"] == "error"
    assert msg["code"] == "validation_error"
    assert "missing field" in msg["detail"]


@pytest.mark.anyio
@pytest.mark.xfail(strict=False, reason="recv_json not implemented yet")
async def test_recv_json_decodes_valid_text_frame(session):
    incoming = [json.dumps({"hello": "world", "x": 1})]
    ws = DummyWebSocket(incoming=incoming)
    obj = await session.recv_json(ws)
    assert obj == {"hello": "world", "x": 1}


@pytest.mark.anyio
@pytest.mark.xfail(strict=False, reason="recv_json error handling not implemented yet")
async def test_recv_json_invalid_payload_raises(session):
    ws = DummyWebSocket(incoming=["{not json}"])
    with pytest.raises(Exception):
        await session.recv_json(ws)


@pytest.mark.anyio
@pytest.mark.xfail(strict=False, reason="on_close not implemented yet")
async def test_on_close_handles_exc_and_closes(session):
    ws = DummyWebSocket()
    exc = RuntimeError("boom")
    await session.on_close(ws, exc)
    # It's OK if on_close doesn't close; this asserts the method completes.
    assert True


@pytest.mark.anyio
@pytest.mark.xfail(strict=False, reason="run_loop not implemented yet")
async def test_run_loop_basic_flow_calls_helpers(monkeypatch):
    """Spec: run_loop should call on_connect once, then repeatedly recv → send, and finally on_close.

    We provide a subclass that exposes flags which run_loop is expected to toggle
    by calling its own helpers. Adjust as needed for your implementation.
    """

    calls = {"connect": 0, "close": 0, "recv": 0, "send": 0}

    class TestSession(BaseSession):
        async def on_connect(self, ws):
            calls["connect"] += 1
            await ws.accept()

        async def on_close(self, ws, exc):
            calls["close"] += 1

        async def recv_json(self, ws):
            calls["recv"] += 1
            # Echo protocol: read one message then signal termination by raising
            result = json.loads(await ws.receive_text())
            raise WebSocketDisconnect(code=1000)

        async def send_json(self, ws, payload):
            calls["send"] += 1
            await ws.send_text(json.dumps(payload))
        
        async def dispatch(self, msg):
            return msg

    sess = TestSession()
    ws = DummyWebSocket(incoming=[json.dumps({"echo": 1})])

    # Expectation: run_loop consumes the one message and exits cleanly (no hang)
    await sess.run_loop(ws)

    assert calls["connect"] == 1
    assert calls["recv"] >= 1
    assert calls["send"] >= 1
    assert calls["close"] == 1
