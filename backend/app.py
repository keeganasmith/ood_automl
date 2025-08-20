from __future__ import annotations
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Tuple, Union, Literal

from fastapi import FastAPI, WebSocket

app = FastAPI()


# ============================== WebSocket endpoints (minimal) ==============================

@app.websocket("/modify_dataset")
async def ws_modify_dataset_endpoint(websocket: WebSocket):
    """
    Allow the user to modify the dataset:
      - view possibly problematic rows
      - change rows, or replace all occurrences of a value in a column
      - delete columns or rows
      - undo operations
      - save to a file (or overwrite existing file)
      - attempt to coerce the type of a column

    Only send a few dozen rows at a time; keep a cursor for the last index sent.
    """
    await handle_modify_dataset_session(websocket)


@app.websocket("/create_run")
async def ws_run_endpoint(websocket: WebSocket):
    """
    From client dataset + config options, run an AutoGluon process that can be
    paused, resumed, restarted, or cancelled by the user.

    Client provides a JSON config with:
      - path to dataset
      - automl parameters
          - type of model/dataset (tabular/multi-model/time-series) (required)
          - amount of time (required)
          - target column (required)
          - problem type (required)
          - eval metric (optional)
          - presets (optional)
      - path to save models / checkpoints
    """
    await handle_create_run_session(websocket)


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


# ============================== Session drivers (declare only) ==============================

async def handle_modify_dataset_session(websocket: WebSocket) -> None:
    """Accept the connection and run the modify-dataset message loop."""
    raise NotImplementedError


async def handle_create_run_session(websocket: WebSocket) -> None:
    """Accept the connection and run the AutoGluon run-control message loop."""
    raise NotImplementedError


# ============================== Common WS utilities (declare only) ==============================

async def ws_accept(websocket: WebSocket) -> None:
    """Accept the WebSocket and perform any auth/handshake as needed."""
    raise NotImplementedError


async def ws_receive_json(websocket: WebSocket) -> Dict[str, Any]:
    """Receive a single JSON message from the client and validate its shape."""
    raise NotImplementedError


async def ws_send_json(websocket: WebSocket, message: Dict[str, Any]) -> None:
    """Send a structured JSON event to the client."""
    raise NotImplementedError


async def ws_send_error(websocket: WebSocket, detail: str, code: str = "bad_request") -> None:
    """Send a standardized error payload."""
    raise NotImplementedError


# ============================== /modify_dataset helpers (declare only) ==============================

async def md_load_dataset(path: str) -> ModifyDatasetState:
    """Load dataset from disk into an editable in-memory state."""
    raise NotImplementedError


async def md_view_rows(state: ModifyDatasetState, start: int, limit: int) -> Tuple[List[Dict[str, Any]], int]:
    """
    Return up to `limit` rows starting at `start`, and the next cursor.
    Returns: (rows, next_cursor)
    """
    raise NotImplementedError


async def md_view_problematic_rows(state: ModifyDatasetState, limit: int) -> List[Dict[str, Any]]:
    """Return rows that have nulls, type errors, or rule violations (up to limit)."""
    raise NotImplementedError


async def md_change_rows(state: ModifyDatasetState, rows: List[Dict[str, Any]]) -> int:
    """Apply partial updates to specific rows; return count of rows changed."""
    raise NotImplementedError


async def md_replace_value(
    state: ModifyDatasetState,
    column: str,
    old: Any,
    new: Any,
    scope: Literal["all", "row_indices"],
    row_indices: Optional[List[int]] = None,
) -> int:
    """Replace occurrences of a value; return affected count."""
    raise NotImplementedError


async def md_delete_columns(state: ModifyDatasetState, columns: List[str]) -> None:
    """Delete columns from the dataset."""
    raise NotImplementedError


async def md_delete_rows(state: ModifyDatasetState, row_indices: List[int]) -> int:
    """Delete rows by index; return count deleted."""
    raise NotImplementedError


async def md_undo(state: ModifyDatasetState) -> None:
    """Revert the most recent operation from the undo stack."""
    raise NotImplementedError


async def md_save(state: ModifyDatasetState, path: str, overwrite: bool) -> str:
    """Persist the current dataset to `path`; return the written path."""
    raise NotImplementedError


async def md_coerce_type(state: ModifyDatasetState, column: str, to: str) -> None:
    """Attempt to coerce a column's dtype (e.g., to int, float, category, datetime)."""
    raise NotImplementedError


async def md_get_summary(state: ModifyDatasetState) -> Dict[str, Any]:
    """Return column names, dtypes, total_rows, and cursor position."""
    raise NotImplementedError


async def md_dispatch(state: Optional[ModifyDatasetState], message: Dict[str, Any]) -> Tuple[Optional[ModifyDatasetState], Dict[str, Any]]:
    """
    High-level dispatcher: apply a modify-dataset action and return
    (possibly updated) state and a response payload to send to client.
    """
    raise NotImplementedError


# ============================== /create_run helpers (declare only) ==============================

AutoMLType = Literal["tabular", "multimodal", "timeseries"]

async def run_validate_config(cfg: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Validate required fields (type, time_limit, target_column, problem_type, etc.)."""
    raise NotImplementedError


async def run_start(cfg: Dict[str, Any]) -> str:
    """Start an AutoGluon run and return a run_id."""
    raise NotImplementedError


async def run_pause(run_id: str) -> None:
    """Pause a running job (cooperative if needed)."""
    raise NotImplementedError


async def run_resume(run_id: str) -> None:
    """Resume a paused job."""
    raise NotImplementedError


async def run_cancel(run_id: str) -> None:
    """Cancel a running job and clean up intermediates (best effort)."""
    raise NotImplementedError


async def run_restart(run_id: str) -> str:
    """Restart a job (optionally from checkpoints) and return a new run_id."""
    raise NotImplementedError


async def run_status(run_id: str) -> Dict[str, Any]:
    """Return current status/progress/metrics for a run."""
    raise NotImplementedError


async def run_stream_progress(
    run_id: str,
    on_event: Callable[[Dict[str, Any]], Awaitable[None]],
) -> None:
    """Continuously emit progress events until completion/cancel."""
    raise NotImplementedError


async def run_dispatch(message: Dict[str, Any]) -> Dict[str, Any]:
    """High-level dispatcher for run control actions (start/pause/resume/restart/cancel/status)."""
    raise NotImplementedError
