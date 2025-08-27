# tests/test_jobrunner.py
import asyncio
import logging
import sys
import time
import types
import uuid
import pytest

# ---- import your JobRunner from the module that defines it ----
# from yourmodule.sessions import JobRunner
from sessions import JobRunner  # adjust import to your project layout


# ---------- Helpers: fake AutoGluon (no heavy deps required) ----------

class _FakeTabularPredictor:
    """Minimal stand-in for autogluon.tabular.TabularPredictor."""
    def __init__(self, label, path, problem_type=None):
        self.label = label
        self.path = path
        self.problem_type = problem_type

    def fit(
        self,
        train_data=None,
        tuning_data=None,
        hyperparameters=None,
        presets=None,
        time_limit=None,
        verbosity=2,
    ):
        # Emit a few log lines through the 'autogluon' logger to exercise the log bridge
        lg = logging.getLogger("autogluon")
        lg.info("fit: start")
        for i in range(3):
            time.sleep(0.05)  # simulate work in the background thread
            lg.info("fit: step %d/3", i + 1)
        lg.info("fit: end")


@pytest.fixture(autouse=True)
def stub_autogluon(monkeypatch):
    """
    Auto-use fixture that creates a fake `autogluon.tabular.TabularPredictor`
    so tests don't require the real AutoGluon package.
    """
    fake_autogluon = types.ModuleType("autogluon")
    fake_tabular = types.ModuleType("autogluon.tabular")
    fake_tabular.TabularPredictor = _FakeTabularPredictor
    fake_autogluon.tabular = fake_tabular

    # Inject into sys.modules so `from autogluon.tabular import TabularPredictor` works
    monkeypatch.setitem(sys.modules, "autogluon", fake_autogluon)
    monkeypatch.setitem(sys.modules, "autogluon.tabular", fake_tabular)
    yield
    # (pytest will restore sys.modules entries via monkeypatch automatically)


# ---------- asyncio helpers ----------
@pytest.mark.asyncio
async def test_validate_requires_label_and_data():
    jr = JobRunner()

    ok, err = await jr.validate({"train_df": object()})
    assert not ok and "label" in err.lower()

    ok, err = await jr.validate({"label": "y"})
    assert not ok and "training data" in err.lower()

    ok, err = await jr.validate({"label": "y", "train_df": object()})
    assert ok and err is None


@pytest.mark.asyncio
async def test_start_streams_logs_and_finishes():
    jr = JobRunner()

    cfg = {
        "label": "y",
        "train_df": object(),
        "path": f"./autogluon_runs/{uuid.uuid4().hex}",
        "presets": "medium_quality_faster_train",
    }

    run_id = await jr.start(cfg)
    assert isinstance(run_id, str)
    assert jr.is_running

    events = []

    async def emit(ev):
        events.append(ev)

    # Stream until EOF (method returns after internal sentinel)
    await asyncio.wait_for(jr.stream_progress(run_id, emit), timeout=5.0)

    # We should have received multiple log events and a finished event
    types_seen = {e.get("type") for e in events}
    assert "log" in types_seen
    assert "finished" in types_seen
    assert "eof" not in types_seen  # EOF is internal and should not be forwarded

    # Check final status
    st = await jr.status(run_id)
    assert st["state"] == "finished"
    assert st["result_path"] is not None
    assert st["error"] is None
    assert st["active"] is False

    # Ensure we can start again (handler cleanup, thread ended)
    run_id2 = await jr.start(cfg)
    assert run_id2 != run_id
    await asyncio.wait_for(jr.stream_progress(run_id2, emit), timeout=5.0)
    st2 = await jr.status(run_id2)
    assert st2["state"] == "finished"


@pytest.mark.asyncio
async def test_single_run_enforced():
    jr = JobRunner()
    cfg = {"label": "y", "train_df": object()}

    # Start first run
    _ = await jr.start(cfg)
    assert jr.is_running

    # Attempt a second start before completion should fail
    with pytest.raises(RuntimeError):
        await jr.start(cfg)

    # Drain the stream so the first run can finish
    events = []

    async def emit(ev):
        events.append(ev)

    # We don't know the run_id here (private), but stream_progress uses internal queue only.
    # Just wait a bit and then verify it's no longer running.
    await asyncio.sleep(0.2)
    # Try to get status; we need the current run_id; ask JobRunner directly isn't exposed,
    # so instead just wait until .is_running flips false:
    for _ in range(100):
        if not jr.is_running:
            break
        await asyncio.sleep(0.05)
    assert not jr.is_running


@pytest.mark.asyncio
async def test_status_running_then_finished():
    jr = JobRunner()
    cfg = {"label": "y", "train_df": object()}

    run_id = await jr.start(cfg)
    st_running = await jr.status(run_id)
    assert st_running["state"] in {"starting", "running"}

    # Consume progress to completion
    async def emit(_):  # discard
        pass

    await asyncio.wait_for(jr.stream_progress(run_id, emit), timeout=5.0)
    st_done = await jr.status(run_id)
    assert st_done["state"] == "finished"
    assert st_done["error"] is None
    assert st_done["active"] is False
