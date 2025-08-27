# tests/test_run_control_session.py
import asyncio
import json
import pytest

# adjust these imports to match your project layout
from sessions import RunControlSession, SUCCESS_MESSAGE


# --------- Fakes / stubs ---------

class FakeWebSocket:
    def __init__(self):
        self.sent_texts = []
        self.accepted = False

    async def accept(self):
        self.accepted = True

    # Not used in these tests (we call dispatch directly),
    # but present to satisfy BaseSession signature if needed.
    async def receive_text(self):
        raise RuntimeError("Not used in these tests")

    async def send_text(self, text: str):
        self.sent_texts.append(text)


class StubJobRunner:
    """A minimal JobRunner stub that emits a fixed list of events and tracks state."""
    def __init__(self, *, validate_ok=True, validate_err=None, is_running=False, emitted_events=None):
        self.validate_ok = validate_ok
        self.validate_err = validate_err
        self.is_running = is_running
        self.started = False
        self.cancelled = False
        self._run_id = "run-stub-1"
        self._state = "idle"
        self._events = emitted_events or [
            {"type": "log", "logger": "autogluon", "level": "info", "msg": "fit: start"},
            {"type": "milestone", "stage": "fit_begin"},
            {"type": "log", "logger": "autogluon", "level": "info", "msg": "fit: end"},
            {"type": "finished", "result_path": f"./autogluon_runs/{_run_id if ' _' == 'nope' else 'run-stub-1'}"},
        ]

    async def validate(self, cfg):
        return (self.validate_ok, self.validate_err)

    async def start(self, cfg):
        self.started = True
        self.is_running = True
        self._state = "running"
        return self._run_id

    async def stream_progress(self, run_id, emit):
        # emit each event, then end (simulate finish)
        for ev in self._events:
            await emit({**ev, "run_id": run_id})
            # yield to loop so the session can send_json
            await asyncio.sleep(0)
        self.is_running = False
        self._state = "finished"

    async def pause(self, run_id):  # not used here
        raise NotImplementedError

    async def resume(self, run_id):  # not used here
        raise NotImplementedError

    async def cancel(self, run_id):
        self.cancelled = True

    async def restart(self, run_id):
        raise NotImplementedError

    async def status(self, run_id):
        return {
            "run_id": run_id,
            "state": self._state,
            "result_path": f"./autogluon_runs/{run_id}" if self._state == "finished" else None,
            "error": None,
            "active": self.is_running,
        }


# --------- Tests ---------

@pytest.mark.asyncio
async def test_start_streams_events_and_clears_curr_run_id():
    jr = StubJobRunner()
    session = RunControlSession(jr)

    # attach a fake websocket (the session normally sets this in on_connect)
    ws = FakeWebSocket()
    await session.on_connect(ws)

    # start
    resp = await session.dispatch({"action_type": "start", "cfg": {"label": "y", "train_df": object()}})
    assert resp["status"] == "success"
    assert "run_id" in resp
    run_id = resp["run_id"]
    assert session.curr_run_id == run_id
    assert ws.accepted

    # allow the background stream task to flush events
    # (stream_progress returns quickly in our stub)
    # poll until curr_run_id is cleared by the cleanup
    for _ in range(100):
        if session.curr_run_id is None:
            break
        await asyncio.sleep(0.01)
    assert session.curr_run_id is None

    # inspect what was sent to the client
    sent = [json.loads(s) for s in ws.sent_texts]
    print(sent)
    # all should be normalized with "type":"event" and "subtype" set from payload "type"
    assert all(msg.get("type") == "event" for msg in sent)
    subtypes = [msg.get("subtype") for msg in sent]
    assert "log" in subtypes
    assert "milestone" in subtypes
    assert "finished" in subtypes

    # the run_id is propagated
    assert all(msg.get("run_id") == run_id for msg in sent)

    # status should be 'finished' now
    st = await session.status(run_id)
    assert st["status"] == "success"
    assert st["run"]["state"] == "finished"
    assert st["run"]["active"] is False


@pytest.mark.asyncio
async def test_start_denied_when_runner_already_running():
    jr = StubJobRunner(is_running=True)  # already busy
    session = RunControlSession(jr)
    ws = FakeWebSocket()
    await session.on_connect(ws)

    resp = await session.dispatch({"action_type": "start", "cfg": {"label": "y", "train_df": object()}})
    assert resp["status"] == "error"
    assert "already in progress" in resp["error"]


@pytest.mark.asyncio
async def test_start_validation_error_bubbles_up():
    jr = StubJobRunner(validate_ok=False, validate_err="missing label")
    session = RunControlSession(jr)
    ws = FakeWebSocket()
    await session.on_connect(ws)

    resp = await session.dispatch({"action_type": "start", "cfg": {"train_df": object()}})
    assert resp["status"] == "error"
    assert "missing label" in resp["error"]


@pytest.mark.asyncio
async def test_status_without_active_run_returns_error():
    jr = StubJobRunner()
    session = RunControlSession(jr)
    ws = FakeWebSocket()
    await session.on_connect(ws)

    resp = await session.dispatch({"action_type": "status"})
    assert resp["status"] == "error"
    assert "no active run" in resp["error"]


@pytest.mark.asyncio
async def test_cancel_without_active_run_returns_error():
    jr = StubJobRunner()
    session = RunControlSession(jr)
    ws = FakeWebSocket()
    await session.on_connect(ws)

    resp = await session.dispatch({"action_type": "cancel"})
    assert resp["status"] == "error"
    assert "no active run" in resp["error"]


@pytest.mark.asyncio
async def test_status_and_cancel_paths():
    jr = StubJobRunner()
    session = RunControlSession(jr)
    ws = FakeWebSocket()
    await session.on_connect(ws)

    # start a run
    start = await session.dispatch({"action_type": "start", "cfg": {"label": "y", "train_df": object()}})
    run_id = start["run_id"]

    # ask for status by explicit run_id
    st = await session.dispatch({"action_type": "status", "run_id": run_id})
    assert st["status"] == "success"
    assert st["run"]["state"] in {"running", "finished"}

    # call cancel (our stub implements cancel without raising)
    resp = await session.dispatch({"action_type": "cancel", "run_id": run_id})
    assert resp == SUCCESS_MESSAGE
