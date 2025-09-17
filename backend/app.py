from __future__ import annotations
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Tuple, Union, Literal
import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, APIRouter, HTTPException,  WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
# Import your sessions + runner
from Modify_Session import ModifyDatasetSession
from Run_Session import JobRunner, RunControlSession, HISTORIC_JOBS_FILE
import pickle
import asyncio
import anyio
import pandas as pd
from autogluon.tabular import TabularPredictor

from pydantic import BaseModel, Field
def _expand(p: str) -> str:
    return os.path.abspath(os.path.expanduser(p))

class InferenceRequest(BaseModel):
    test_path: str = Field(..., description="Path to test data (CSV or Parquet)")
    job_id: str = Field(..., description="ID of the AutoGluon job")
    output_path: str = Field(..., description="File path where predictions will be written (CSV)")
    proba: bool = Field(False, description="If true, write predict_proba instead of class labels")

BASE_URL = os.getenv("BASE_URL", "")

app = FastAPI(title="Run Controller API")

"""
prefix_router = APIRouter(prefix=BASE_URL)
print("base url is: ", BASE_URL)
app.include_router(prefix_router)
"""
    

# --------------------------------------------------------------------------------------
# Shared singleton JobRunner (enforces at-most-one AutoGluon run across all connections)
# --------------------------------------------------------------------------------------
# ============================== HTTP endpoints ==============================

@app.get(BASE_URL + "/healthz")
async def healthz():
    return JSONResponse({"ok": True, "runner_active": job_runner.is_running})

# (Optional) expose a super-minimal status endpoint if you have a run_id handy.
# Typically, status is queried via the websocket "status" action, but you can
# add an HTTP status endpoint later if desired.

# ============================== WebSocket endpoints ==============================

# If/when you implement dataset editing, you can uncomment:
# @app.websocket("/modify_dataset")
# async def ws_modify_dataset_endpoint(ws: WebSocket):
#     await ModifyDatasetSession().run_loop(ws)

job_runner = JobRunner()
@app.websocket(BASE_URL + "/create_run")
async def ws_run_endpoint(ws: WebSocket):
    # Each websocket gets its own session, but they all share the same job_runner
    # so only one AutoGluon run can be active at a time.
    await RunControlSession(job_runner=job_runner).run_loop(ws)

@app.get(BASE_URL + "/running_job")
async def get_running_jobs():
    if(job_runner.is_running):
      return JSONResponse({"ok": True, "run_id": job_runner._run_id})
    return JSONResponse({"ok": True, "run_id": ""})

@app.get(BASE_URL + "/historic_jobs")
async def get_historic_jobs():
    print("got to historic jobs endpoint")
    with open(HISTORIC_JOBS_FILE, "rb") as my_file:
      job_id_mapping = pickle.load(my_file)
    return JSONResponse({"ok": True, "job_ids": list(job_id_mapping.keys())})

@app.get(BASE_URL + "/job/{job_id}")
async def get_job(job_id: str):
    with open(HISTORIC_JOBS_FILE, "rb") as my_file:
      job_id_mapping = pickle.load(my_file)
    file_path = job_id_mapping[job_id]["file_path"]
    config = job_id_mapping[job_id]["cfg"]
    with open(file_path, "r") as my_file:
      log_file_content = my_file.read()
    return JSONResponse({"ok": True, "job_id": job_id, "log_content": log_file_content, "cfg": config})

def _locate_predictor_dir(job_dir: str) -> Optional[str]:
    """
    Try common locations or discover by finding 'learner.pkl'.
    Returns the directory passed to TabularPredictor.load(...)
    """
    # 1) Explicit hints in mapping (if you store them)
    for hint in ("predictor_path", "model_path", "result_path"):
        # caller can pass these via job_map if available
        pass

    # 2) Common subdirs
    candidates = [
        os.path.join(job_dir, "predictor"),
        os.path.join(job_dir, "artifacts"),
        job_dir,  # sometimes predictor is saved directly in job_dir
    ]
    for c in candidates:
        if os.path.isfile(os.path.join(c, "learner.pkl")):
            return c

    # 3) Search shallowly for learner.pkl (depth-limited)
    max_depth = 3
    base_parts = _expand(job_dir).rstrip(os.sep).split(os.sep)
    for root, dirs, files in os.walk(job_dir):
        depth = len(_expand(root).split(os.sep)) - len(base_parts)
        if depth > max_depth:
            # prune deeper traversal
            dirs[:] = []
            continue
        if "learner.pkl" in files:
            return root
    return None


def _read_frame(path: str) -> pd.DataFrame:
    if path.lower().endswith(".csv"):
        return pd.read_csv(path)
    if path.lower().endswith(".parquet"):
        return pd.read_parquet(path)
    # Default to CSV if extension unknown
    return pd.read_csv(path)


def _write_frame(df: pd.DataFrame, path: str) -> None:
    parent = os.path.dirname(path)
    if parent and not os.path.exists(parent):
        os.makedirs(parent, exist_ok=True)
    df.to_csv(path, index=False)


def _predict_sync(predictor_dir: str, test_path: str, out_path: str, proba: bool) -> dict:
    if TabularPredictor is None:
        raise RuntimeError("AutoGluon not installed. pip install autogluon.tabular")

    predictor = TabularPredictor.load(predictor_dir)
    df = _read_frame(test_path)

    if proba:
        # predict_proba returns DataFrame (multiclass) or Series (binary)
        proba_out = predictor.predict_proba(df)
        if isinstance(proba_out, pd.Series):
            proba_out = proba_out.to_frame("proba")
        proba_out.insert(0, "row", range(len(proba_out)))
        _write_frame(proba_out, out_path)
        n_rows = len(proba_out)
        cols = list(proba_out.columns)
    else:
        preds = predictor.predict(df)
        out = pd.DataFrame({"prediction": preds})
        out.insert(0, "row", range(len(out)))
        _write_frame(out, out_path)
        n_rows = len(out)
        cols = list(out.columns)

    return {"rows": n_rows, "columns": cols}

@app.post(BASE_URL + "/inference")
async def run_inference(req: InferenceRequest):
    # Resolve paths
    test_path = _expand(req.test_path)
    out_path = _expand(req.output_path)

    # Validate inputs
    if not os.path.exists(test_path):
        raise HTTPException(status_code=404, detail=f"test_path not found: {test_path}")

    with open(HISTORIC_JOBS_FILE, "rb") as f:
      job_map = pickle.load(f)
    
    job_id = req.job_id
    predictor_dir = job_map[job_id]["file_path"]
    try:
        result = await anyio.to_thread.run_sync(
            _predict_sync, predictor_dir, test_path, out_path, req.proba
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Inference failed: {e}")

    return JSONResponse(
        {
            "ok": True,
            "job_id": req.job_id,
            "predictor_dir": predictor_dir,
            "test_path": test_path,
            "output_path": out_path,
            "proba": req.proba,
            "result": result,
        }
    ) 

@app.websocket(BASE_URL + "/ws")
async def ws_file_stream(ws: WebSocket, job_id: str):
    await ws.accept()
    try:
        # look up the job directory from the pickle
        with open(HISTORIC_JOBS_FILE, "rb") as f:
            job_map = pickle.load(f)

        info = job_map.get(job_id)
        if not info:
            await ws.send_text("ERROR: unknown job_id")
            await ws.close(code=1003)
            return

        job_dir = info["file_path"]
        log_path = os.path.join(job_dir, "logs", "predictor_log.txt")

        if not os.path.isfile(log_path):
            await ws.send_text(f"ERROR: log file not found: {log_path}")
            await ws.close(code=1003)
            return

        await ws.send_text(f"INFO: streaming {log_path}")

        # stream the file (tail -f style): send lines as they appear
        import aiofiles
        async with aiofiles.open(log_path, "r") as f:
            while True:
                line = await f.readline()
                if line:
                    await ws.send_text(line)
                else:
                    await asyncio.sleep(0.5)

    except WebSocketDisconnect:
        return
    except Exception as e:
        try:
            await ws.send_text(f"ERROR: {e}")
        finally:
            await ws.close(code=1011)


# frontend rendering
# --- Static site (Vue build) ---
DIST_DIR = (Path(__file__).parent.parent / "frontend" / "run-client" / "dist").resolve()

# Serve built assets (JS/CSS/images)
app.mount("/assets", StaticFiles(directory=DIST_DIR / "assets"), name="assets")

# Serve index.html at root
@app.get(BASE_URL + "/", response_class=HTMLResponse)
async def index():
  return FileResponse(DIST_DIR / "index.html")

# SPA fallback for client-side routes (but don’t shadow your API)
@app.get(BASE_URL + "/{path:path}", response_class=HTMLResponse)
async def spa_fallback(path: str):
  # Let API/websocket/static paths 404 normally
  print(path)
  if path.startswith(("healthz", "create_run")):
    raise HTTPException(status_code=404)
  path = "/" + path
  dist_dir = DIST_DIR / path.lstrip("/")
  print(dist_dir)
  return FileResponse(dist_dir)

if __name__ == "__main__":
    # Optional local dev entrypoint:
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
