from __future__ import annotations
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Tuple, Union, Literal

from fastapi import FastAPI, WebSocket
from sessions import ModifyDatasetSession, RunControlSession
app = FastAPI()


# ============================== WebSocket endpoints (minimal) ==============================

@app.websocket("/modify_dataset")
async def ws_modify_dataset_endpoint(ws: WebSocket):
    await ModifyDatasetSession().run_loop(ws)

@app.websocket("/create_run")
async def ws_run_endpoint(ws: WebSocket):
    await RunControlSession(job_runner=JobRunner()).run_loop(ws)


# ============================== Helper type stubs ==============================

# You can replace these with dataclasses or pydantic models later.
ModifyAction = Literal[
    "load_dataset",
    "view_rows",
    "view_problematic_rows",
    "change_rows",
    "replace_value",
    "delete_columns",
    "delete_rows",
    "undo",
    "save",
    "coerce_type",
]

RunAction = Literal["start", "pause", "resume", "restart", "cancel", "status"]

class ModifyDatasetState:  # pragma: no cover - stub type
    """In-memory working copy, cursor, undo stack, schema, etc."""
    ...
