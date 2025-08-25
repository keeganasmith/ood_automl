# sessions.py (stubs; define later)
from typing import Any, Dict, Awaitable, Callable, Optional
from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json
from abc import ABC, abstractmethod

class BaseSession:
    async def run_loop(self, ws):
        """
        Lifecycle:
          1) on_connect(ws)           – handshake/auth
          2) Loop:
               msg = recv_json(ws)    – one message from client
               resp = dispatch(msg)   – subclass provides business logic
               send_json(ws, resp)    – optional; only if resp is not None
             Handle JSON/validation errors with send_error(ws, ...).
             Exit cleanly on disconnect.
          3) on_close(ws, exc)        – cleanup (exc is the terminal exception, if any)
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
                    # continue the loop and wait for the next message
                    continue

                try:
                    # Subclasses should implement dispatch(msg) -> Optional[Dict]
                    resp = await self.dispatch(msg)  # type: ignore[attr-defined]
                except WebSocketDisconnect as e:
                    exc = e
                    break
                except asyncio.CancelledError as e:
                    exc = e
                    break
                except Exception as e:
                    await self.send_error(ws, f"server error: {e}", code="server_error")
                    # choose to continue or break; continue keeps the session alive
                    continue

                if resp is not None:
                    await self.send_json(ws, resp)
        finally:
            await self.on_close(ws, exc)


    async def on_connect(self, ws):
        await ws.accept()

    async def on_close(self, ws, exc: Optional[BaseException]): ...
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
            # Surface a clear error if the payload isn't JSON-serializable
            raise ValueError(f"send_json payload not serializable: {e}") from e
        await ws.send_text(text)


    async def send_error(self, ws, detail: str, code: str = "bad_request") -> None:
        payload: Dict[str, Any] = {
            "type": "error",
            "code": str(code),
            "detail": str(detail),
        }
        await self.send_json(ws, payload)

class ModifyDatasetSession(BaseSession):
    def __init__(self):
        self.cursor = 0
        self.undo_stack = []
        self.df = None  # lazy-loaded

    async def dispatch(self, msg: Dict[str, Any]) -> Dict[str, Any]: ...
    async def load_dataset(self, path: str) -> Dict[str, Any]: ...
    async def view_rows(self, start: int, limit: int) -> Dict[str, Any]: ...
    async def view_problematic_rows(self, limit: int) -> Dict[str, Any]: ...
    async def change_rows(self, rows: list[dict]) -> Dict[str, Any]: ...
    async def replace_value(self, column: str, old: Any, new: Any, scope: str, row_indices=None) -> Dict[str, Any]: ...
    async def delete_columns(self, columns: list[str]) -> Dict[str, Any]: ...
    async def delete_rows(self, row_indices: list[int]) -> Dict[str, Any]: ...
    async def undo(self) -> Dict[str, Any]: ...
    async def save(self, path: str, overwrite: bool) -> Dict[str, Any]: ...
    async def coerce_type(self, column: str, to: str) -> Dict[str, Any]: ...

class RunControlSession(BaseSession):
    def __init__(self, job_runner):
        self.job_runner = job_runner
        self.run_id: Optional[str] = None

    async def dispatch(self, msg: Dict[str, Any]) -> Dict[str, Any]: ...
    async def start(self, cfg: Dict[str, Any]) -> Dict[str, Any]: ...
    async def pause(self) -> Dict[str, Any]: ...
    async def resume(self) -> Dict[str, Any]: ...
    async def restart(self) -> Dict[str, Any]: ...
    async def cancel(self) -> Dict[str, Any]: ...
    async def status(self) -> Dict[str, Any]: ...

class JobRunner:
    async def validate(self, cfg: Dict[str, Any]) -> tuple[bool, Optional[str]]: ...
    async def start(self, cfg: Dict[str, Any]) -> str: ...
    async def pause(self, run_id: str) -> None: ...
    async def resume(self, run_id: str) -> None: ...
    async def cancel(self, run_id: str) -> None: ...
    async def restart(self, run_id: str) -> str: ...
    async def status(self, run_id: str) -> Dict[str, Any]: ...
    async def stream_progress(self, run_id: str, emit: Callable[[Dict[str, Any]], Awaitable[None]]) -> None: ...
