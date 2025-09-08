from __future__ import annotations
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Tuple, Union, Literal
import os
from fastapi import FastAPI, WebSocket, APIRouter
from fastapi.responses import JSONResponse

# Import your sessions + runner
from Modify_Session import ModifyDatasetSession
from Run_Session import JobRunner, RunControlSession

BASE_URL = os.getenv("BASE_URL", "")  # e.g. "/node/lc05/42801"

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
@app.get(BASE_URL + "/")
async def root():
    return JSONResponse({"ok": True})

# ============================== HTTP endpoints ==============================

@app.get("/healthz")
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

@app.websocket("/create_run")
async def ws_run_endpoint(ws: WebSocket):
    # Each websocket gets its own session, but they all share the same job_runner
    # so only one AutoGluon run can be active at a time.
    await RunControlSession(job_runner=job_runner).run_loop(ws)


if __name__ == "__main__":
    # Optional local dev entrypoint:
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
