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
from Base_Session import BaseSession
import os
import pickle
from autogluon.tabular import TabularPredictor
from autogluon.multimodal import MultiModalPredictor
from autogluon.timeseries import TimeSeriesDataFrame, TimeSeriesPredictor
import torch
from autogluon.common.utils.log_utils import add_log_to_file
import traceback
from autogluon.common.utils.resource_utils import ResourceManager
from datetime import datetime
import multiprocessing as mp
NUM_GPUS = 0
if torch.cuda.is_available():
    NUM_GPUS = torch.cuda.device_count()
print("num_gpus: ", NUM_GPUS)
HISTORIC_JOBS_DIRECTORY = os.path.expanduser("~/.ood_automl")
print(HISTORIC_JOBS_DIRECTORY)
if not os.path.exists(HISTORIC_JOBS_DIRECTORY):
    os.makedirs(HISTORIC_JOBS_DIRECTORY)
HISTORIC_JOBS_FILE = HISTORIC_JOBS_DIRECTORY + "/runs_index.pkl"
if not os.path.exists(HISTORIC_JOBS_FILE):
    with open(HISTORIC_JOBS_FILE, 'wb+') as my_file:
        pickle.dump({}, my_file)

def _setup_log_to_file(log_file_path: str):
    log_file_path = os.path.abspath(os.path.normpath(log_file_path))
    os.makedirs(os.path.dirname(log_file_path), exist_ok=True)
    add_log_to_file(log_file_path)

SUCCESS_MESSAGE = {"status": "success"}
class _AsyncQueueLogHandler(logging.Handler):
    """Logging handler that pushes log records into an asyncio.Queue from any thread."""
    def __init__(self, loop: asyncio.AbstractEventLoop, queue: asyncio.Queue, run_id: str):
        super().__init__()
        self.loop = loop
        self.queue = queue
        self.run_id = run_id

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        payload = {
            "run_id": self.run_id,
            "type": "log",
            "logger": record.name,
            "level": record.levelname.lower(),
            "msg": msg,
        }
        # safe from non-async threads
        asyncio.run_coroutine_threadsafe(self.queue.put(payload), self.loop)

class _MPQueueLogHandler(logging.Handler):
    """Logging handler that pushes log records into a multiprocessing.Queue."""
    def __init__(self, queue: mp.Queue, run_id: str):
        super().__init__()
        self.queue = queue
        self.run_id = run_id

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
        except Exception:
            msg = record.getMessage()
        payload = {
            "run_id": self.run_id,
            "type": "log",
            "logger": record.name,
            "level": record.levelname.lower(),
            "msg": msg,
        }
        try:
            self.queue.put_nowait(payload)
        except Exception:
            # avoid crashing on queue issues
            pass


def _worker_train_entry(
    cfg: Dict[str, Any],
    run_id: str,
    q: mp.Queue,
) -> None:
    """Runs inside the child process; does the AutoGluon fit."""
    def notify(payload: Dict[str, Any]) -> None:
        try:
            q.put(payload)
        except Exception:
            pass

    try:
        # install logging bridge in worker
        handler = _MPQueueLogHandler(q, run_id)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(asctime)s %(name)s: %(message)s"))

        root = logging.getLogger()
        root.addHandler(handler)
        root.setLevel(min(root.level, logging.INFO) if root.level else logging.INFO)
        logging.getLogger("autogluon").setLevel(logging.INFO)

        notify({"run_id": run_id, "type": "milestone", "stage": "imported_autogluon"})

        label = cfg["label"]
        path = cfg.get("path") or f"./autogluon_runs/{run_id}"
        cfg["path"] = path
        presets = cfg.get("presets", "medium_quality")
        time_limit = cfg.get("time_limit")  # seconds
        hyperparameters = cfg.get("hyperparameters")
        problem_type = cfg.get("problem_type")
        data_type = cfg.get("data_type")
        if cfg.get("num_gpus") == 0 or cfg.get("enable_gpu") is False:
            requested_num_gpus = 0
        else:
            requested_num_gpus = NUM_GPUS
        cfg["num_gpus"] = requested_num_gpus

        train_data = cfg.get("train_df")
        if cfg.get("train_path"):
            train_data = load_table(cfg.get("train_path"))
        tuning_data = cfg.get("tuning_data")

        predictor = None
        if data_type == "tabular":
            predictor = TabularPredictor(
                label=label,
                path=path,
                problem_type=problem_type,
            )
        elif data_type == "mm":
            predictor = MultiModalPredictor(
                label=label,
                path=path,
                problem_type=problem_type,
            )
        elif data_type == "series":
            # --- Time series predictor setup ---
            prediction_length = cfg["prediction_length"]
            id_col = cfg.get("id_column", "item_id")
            time_col = cfg.get("time_column", "timestamp")
            freq = cfg.get("freq")  # optional, e.g. "D", "H", "5min"

            # Ensure train_data is a TimeSeriesDataFrame
            if not isinstance(train_data, TimeSeriesDataFrame):
                train_data = TimeSeriesDataFrame.from_data_frame(
                    train_data,
                    id_column=id_col,
                    timestamp_column=time_col,
                )

            # (Optional) do the same for tuning_data if provided
            if tuning_data is not None and not isinstance(tuning_data, TimeSeriesDataFrame):
                tuning_data = TimeSeriesDataFrame.from_data_frame(
                    tuning_data,
                    id_column=id_col,
                    timestamp_column=time_col,
                )

            predictor = TimeSeriesPredictor(
                prediction_length=prediction_length,
                target=label,
                path=path,
                freq=freq,
            )
        run_log_path = os.path.join(path, "logs", "predictor_log.txt")
        os.makedirs(os.path.dirname(run_log_path), exist_ok=True)

        # write to mapping file (inline, since no self here)
        with open(HISTORIC_JOBS_FILE, "rb") as map_file:
            current_job_id_mapping = pickle.load(map_file)
        current_job_id_mapping[run_id] = {"file_path": path, "cfg": cfg, "start": datetime.now() }
        with open(HISTORIC_JOBS_FILE, "wb") as map_file:
            pickle.dump(current_job_id_mapping, map_file)

        open(run_log_path, "w").close()
        _setup_log_to_file(run_log_path)

        notify({"run_id": run_id, "type": "milestone", "stage": "fit_begin"})

        if data_type == "tabular":
            predictor.fit(
                train_data=train_data,
                tuning_data=tuning_data,
                hyperparameters=hyperparameters,
                presets=presets,
                time_limit=time_limit,
                num_gpus=requested_num_gpus,
                ag_args_fit={"num_gpus": requested_num_gpus},
            )
        elif data_type == "mm":
            predictor.fit(
                train_data=train_data,
                tuning_data=tuning_data,
                hyperparameters=hyperparameters,
                presets=presets,
                time_limit=time_limit,
            )
        elif data_type == "series":
            predictor.fit(
                train_data=train_data,
                tuning_data=tuning_data,
                hyperparameters=hyperparameters,
                presets=presets,
                time_limit=time_limit
            )
        with open(HISTORIC_JOBS_FILE, "rb") as map_file:
            current_job_id_mapping = pickle.load(map_file)
        current_job_id_mapping[run_id]["end"] = datetime.now()
        with open(HISTORIC_JOBS_FILE, "wb") as map_file:
            pickle.dump(current_job_id_mapping, map_file)
        notify({
            "run_id": run_id,
            "type": "finished",
            "result_path": predictor.path,
        })

    except Exception as e:
        tb = "".join(traceback.format_exception(e))
        notify({
            "run_id": run_id,
            "type": "error",
            "error": str(e) + "\n" + tb,
            "traceback": tb,
        })
    finally:
        # signal end of stream
        try:
            q.put({"run_id": run_id, "type": "eof"})
        except Exception:
            pass

class JobRunner:
    
    """
    Executes AutoGluon training and streams progress/logs via an asyncio.Queue.
    Single-run policy enforced (one run at a time).
    """
    def __init__(self) -> None:
        self._active: bool = False
        self._run_id: Optional[str] = None
        self._q: Optional[asyncio.Queue] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        # NEW: process + mp queue
        self._proc: Optional[mp.Process] = None
        self._mp_q: Optional[mp.Queue] = None

        self._stop_evt = threading.Event()
        self._state: str = "idle"
        self._result_path: Optional[str] = None
        self._last_error: Optional[str] = None
        self._run_log_path: Optional[str] = None
        self._path: Optional[str] = None

        # optional: forwarder thread
        self._forward_thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        return self._active

    async def validate(self, cfg: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        # Minimal validation for Tabular: require label and training data or path
        if "label" not in cfg:
            return False, "cfg.label is required"
        if not (("train_df" in cfg) or ("train_data" in cfg) or ("train_path" in cfg)):
            return False, "Provide training data via cfg.train_df/cfg.train_data/cfg.train_path"
        return True, None

    def _forward_worker_events(self) -> None:
        """Runs in a thread: read from mp.Queue and push to asyncio.Queue."""
        if self._mp_q is None:
            return

        while True:
            try:
                item = self._mp_q.get()
            except (EOFError, OSError):
                break

            if item is None:
                continue

            t = item.get("type")

            # keep our internal state in sync for status()
            if t == "finished":
                self._state = "finished"
                self._result_path = item.get("result_path")
            elif t == "error":
                self._state = "error"
                self._last_error = item.get("error")
            elif t == "eof":
                self._active = False

            # push every event to the asyncio queue
            self._notify(item)

            if t == "eof":
                break

        # Clean up process reference once queue is drained
        if self._proc is not None:
            if self._proc.is_alive():
                self._proc.join(timeout=1.0)
            self._proc = None
        self._mp_q = None

    async def start(self, cfg: Dict[str, Any]) -> str:
        if self._active:
            raise RuntimeError("An AutoGluon run is already active")
        self._active = True
        self._state = "starting"
        self._stop_evt.clear()
        self._result_path = None
        self._last_error = None

        self._run_id = uuid.uuid4().hex
        run_id = self._run_id

        self._loop = asyncio.get_running_loop()
        self._q = asyncio.Queue()

        # compute and store log path for your existing log_stream
        path = cfg.get("path") or f"./autogluon_runs/{run_id}"
        self._path = path
        self._run_log_path = os.path.join(path, "logs", "predictor_log.txt")

        # create process queue and process
        self._mp_q = mp.Queue()
        self._proc = mp.Process(
            target=_worker_train_entry,
            args=(cfg, run_id, self._mp_q),
            daemon=False,
        )
        self._proc.start()

        # forward worker -> asyncio queue in a thread
        self._forward_thread = threading.Thread(
            target=self._forward_worker_events,
            daemon=True,
        )
        self._forward_thread.start()

        # announce start
        await self._q.put({"run_id": run_id, "type": "state", "state": "running"})
        return run_id


    def write_to_mapping_file(self, path, cfg):
        with open(HISTORIC_JOBS_FILE, "rb") as map_file:
            current_job_id_mapping = pickle.load(map_file)

        current_job_id_mapping[self._run_id] = {}
        current_job_id_mapping[self._run_id]["file_path"] = path
        current_job_id_mapping[self._run_id]["cfg"] = cfg
        with open(HISTORIC_JOBS_FILE, "wb") as map_file:
            pickle.dump(current_job_id_mapping, map_file)

    def _notify(self, payload: Dict[str, Any]) -> None:
        """Thread-safe push into the queue."""
        if self._loop and self._q:
            asyncio.run_coroutine_threadsafe(self._q.put(payload), self._loop)

    async def pause(self, run_id: str) -> None:
        # Not supported for AutoGluon cleanly; you could implement cooperative checkpoints.
        raise NotImplementedError("pause not supported")

    async def resume(self, run_id: str) -> None:
        raise NotImplementedError("resume not supported")

    async def cancel(self, run_id: str) -> None:
        # hard-cancel via killing the worker process
        if self._proc and self._proc.is_alive():
            self._proc.terminate()
            self._proc.join(timeout=5.0)

        self._active = False
        self._state = "cancelled"
        # tell streamers to stop
        self._notify({"run_id": run_id, "type": "eof"})

    async def restart(self, run_id: str) -> str:
        raise NotImplementedError("restart not supported")

    def log_stream(self, stop_evt: threading.Event):
        current_log_file = ""
        while not stop_evt.is_set():
            if(not (self._run_log_path is None)):
                try:
                    with open(self._run_log_path, "r") as file:
                        log_file_contents = file.read()
                except:
                    continue
                #parsed_log_file = parse_autogluon_log(log_file_contents)["models"]
                if(len(log_file_contents) > len(current_log_file)):
                    #diff = parsed_log_file[len(current_log_file):]
                    diff = log_file_contents[len(current_log_file):]
                    #item = {"type": "log", "msg": diff, "run_id": self._run_id}
                    item = {"type": "log", "msg": diff, "run_id": self._run_id}
                    current_log_file = log_file_contents
                    self._notify(item)
            time.sleep(0)

    async def status(self, run_id: str) -> Dict[str, Any]:
        return {
            "run_id": run_id,
            "state": self._state,
            "result_path": self._result_path,
            "error": self._last_error,
            "active": self._active,
        }

    async def stream_progress(
        self,
        run_id: str,
        emit: Callable[[Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """Drain internal queue and forward to the provided emitter until EOF."""
        self._stop_evt.clear()
        log_thread = threading.Thread(
            target=self.log_stream, args=(self._stop_evt,), daemon=True
        )
        log_thread.start()
        if not self._q:
            return
        try:
            while True:
                item = await self._q.get()
                try:
                    if item.get("type") == "eof":
                        self._stop_evt.set()
                        # don't forward EOF to client; it's internal
                        return
                    await emit(item)

                finally:
                    self._q.task_done()

        except asyncio.CancelledError:
            # If the coroutine is cancelled, also stop the log thread
            self._stop_evt.set()
            await asyncio.to_thread(log_thread.join, 5.0)
            raise

# =========================
# Run control session
# =========================

class RunControlSession(BaseSession):
    """
    Starts exactly one AutoGluon job at a time and streams updates/logs to the client.
    Messages (JSON) it will send to the client (examples):
      {"type":"event","run_id":"...","subtype":"log","level":"info","msg":"..."}
      {"type":"event","run_id":"...","subtype":"milestone","stage":"fit_begin"}
      {"type":"event","run_id":"...","subtype":"finished","result_path":"..."}
      {"type":"event","run_id":"...","subtype":"error","error":"..."}
    """
    def __init__(self, job_runner: JobRunner):
        super().__init__()
        self.job_runner = job_runner
        self.runs: Dict[str, Any] = {}
        self.curr_run_id: Optional[str] = None
        self._progress_task: Optional[asyncio.Task] = None

    async def on_close(self, ws: WebSocket, exc: Optional[BaseException]):
        # Allow the job to continue even if client disconnects; nothing special to do.
        # If you want to auto-cancel on disconnect, call self.job_runner.cancel here.
        pass

    async def dispatch(self, msg: Dict[str, Any]) -> Dict[str, Any]:
        action_type: str = msg.get("action_type", "")
        if action_type == "start":
            cfg = msg["cfg"]
            return await self._handle_start(cfg)
        elif action_type == "status":
            rid = msg.get("run_id") or self.curr_run_id
            if not rid:
                return {"status": "error", "error": "no active run"}
            return await self.status(rid)
        elif action_type == "cancel":
            rid = msg.get("run_id") or self.curr_run_id
            if not rid:
                return {"status": "error", "error": "no active run"}
            return await self.cancel(rid)
        else:
            return {"status": "error", "error": f"unknown action_type={action_type}"}

    async def _handle_start(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        if self.job_runner.is_running:
            return {"status": "error", "error": "a run is already in progress"}
        ok, err = await self.job_runner.validate(cfg)
        if not ok:
            return {"status": "error", "error": err or "invalid cfg"}

        run_id = await self.job_runner.start(cfg)
        self.curr_run_id = run_id

        # Stream progress/logs to the same websocket
        assert self._ws is not None

        async def emit(payload: Dict[str, Any]) -> None:
            # Normalize to a stable envelope for the client
            payload_without_type = copy.deepcopy(payload)
            del payload_without_type["type"]
            await self.send_json(self._ws, {"type": "event", "subtype": payload.get("type"), **payload_without_type})

        async def _stream_and_cleanup():
            with contextlib.suppress(Exception):
                await self.job_runner.stream_progress(run_id, emit)
            # When stream ends, clear active run
            if self.curr_run_id == run_id:
                self.curr_run_id = None

        self._progress_task = asyncio.create_task(_stream_and_cleanup())
        return {"status": "success", "run_id": run_id}

    async def start(self, cfg: Dict[str, Any]) -> Dict[str, Any]:
        # Not called directly; use dispatch("start")
        return await self._handle_start(cfg)

    async def pause(self, run_id: str) -> Dict[str, Any]:
        try:
            await self.job_runner.pause(run_id)
            return SUCCESS_MESSAGE
        except NotImplementedError as e:
            return {"status": "error", "error": str(e)}

    async def resume(self, run_id: str) -> Dict[str, Any]:
        try:
            await self.job_runner.resume(run_id)
            return SUCCESS_MESSAGE
        except NotImplementedError as e:
            return {"status": "error", "error": str(e)}

    async def restart(self, run_id: str) -> Dict[str, Any]:
        try:
            new_id = await self.job_runner.restart(run_id)
            self.curr_run_id = new_id
            return {"status": "success", "run_id": new_id}
        except NotImplementedError as e:
            return {"status": "error", "error": str(e)}

    async def cancel(self, run_id: str) -> Dict[str, Any]:
        try:
            await self.job_runner.cancel(run_id)
            return SUCCESS_MESSAGE
        except NotImplementedError as e:
            return {"status": "error", "error": str(e)}

    async def status(self, run_id: str) -> Dict[str, Any]:
        st = await self.job_runner.status(run_id)
        return {"status": "success", "run": st}
