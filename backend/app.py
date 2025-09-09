from __future__ import annotations
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Tuple, Union, Literal
import os
from pathlib import Path
from fastapi import FastAPI, WebSocket, APIRouter, HTTPException
from fastapi.responses import JSONResponse
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
# Import your sessions + runner
from Modify_Session import ModifyDatasetSession
from Run_Session import JobRunner, RunControlSession

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
job_runner = JobRunner()
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

@app.websocket(BASE_URL + "/create_run")
async def ws_run_endpoint(ws: WebSocket):
    # Each websocket gets its own session, but they all share the same job_runner
    # so only one AutoGluon run can be active at a time.
    await RunControlSession(job_runner=job_runner).run_loop(ws)


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
@app.get("/{path:path}", response_class=HTMLResponse)
async def spa_fallback(path: str):
  # Let API/websocket/static paths 404 normally
  if path.startswith(("assets", "healthz", "create_run")):
    raise HTTPException(status_code=404)
  path = "/" + path
  dist_dir_sub_path = path[path.find(BASE_URL):]
  print(dist_dir_sub_path)
  return FileResponse(DIST_DIR / "index.html")

if __name__ == "__main__":
    # Optional local dev entrypoint:
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
