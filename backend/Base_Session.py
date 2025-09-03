from __future__ import annotations
import copy
from typing import Any, Dict, Awaitable, Callable, Optional, List
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
import uuid
import logging
import threading
import contextlib
from helper import load_table
from contextlib import redirect_stdout, redirect_stderr
from autogluon_log_parser import parse_autogluon_log
import sys
import time
SUCCESS_MESSAGE = {"status": "success"}

# =========================
# Base session wiring
# =========================

class BaseSession:
    def __init__(self) -> None:
        self._ws: Optional[WebSocket] = None

    async def run_loop(self, ws: WebSocket):
        """
        Lifecycle:
          1) on_connect(ws)
          2) Loop: recv_json -> dispatch -> send_json
          3) on_close(ws, exc)
        """
        exc: Optional[BaseException] = None
        await self.on_connect(ws)
        try:
            while True:
                try:
                    msg: Dict[str, Any] = await self.recv_json(ws)
                except WebSocketDisconnect as e:
                    exc = e
                    break
                except asyncio.CancelledError as e:
                    exc = e
                    break
                except Exception as e:
                    await self.send_error(ws, f"bad message: {e}", code="bad_message")
                    continue

                try:
                    resp = await self.dispatch(msg)  # implemented by subclass
                except WebSocketDisconnect as e:
                    exc = e
                    break
                except asyncio.CancelledError as e:
                    exc = e
                    break
                except Exception as e:
                    await self.send_error(ws, f"server error: {e}", code="server_error")
                    continue

                if resp is not None:
                    await self.send_json(ws, resp)
        finally:
            await self.on_close(ws, exc)

    async def on_connect(self, ws: WebSocket):
        self._ws = ws
        await ws.accept()

    async def on_close(self, ws: WebSocket, exc: Optional[BaseException]): ...
    async def dispatch(self, msg: Dict[str, Any]) -> Optional[Dict[str, Any]]: ...

    async def recv_json(self, ws: WebSocket) -> Dict[str, Any]:
        raw = await ws.receive_text()
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON from client: {e.msg}") from e
        if not isinstance(obj, dict):
            raise TypeError("Expected top-level JSON object (dict)")
        return obj

    async def send_json(self, ws: WebSocket, payload: Dict[str, Any]) -> None:
        try:
            text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        except (TypeError, ValueError) as e:
            raise ValueError(f"send_json payload not serializable: {e}") from e
        await ws.send_text(text)

    async def send_error(self, ws: WebSocket, detail: str, code: str = "bad_request") -> None:
        payload: Dict[str, Any] = {
            "type": "error",
            "code": str(code),
            "detail": str(detail),
        }
        await self.send_json(ws, payload)