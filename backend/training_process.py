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
        presets = cfg.get("presets", "medium_quality_faster_train")
        time_limit = cfg.get("time_limit")  # seconds
        hyperparameters = cfg.get("hyperparameters")
        problem_type = cfg.get("problem_type")
        data_type = cfg.get("data_type")

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

        run_log_path = os.path.join(path, "logs", "predictor_log.txt")
        os.makedirs(os.path.dirname(run_log_path), exist_ok=True)

        # write to mapping file (inline, since no self here)
        with open(HISTORIC_JOBS_FILE, "rb") as map_file:
            current_job_id_mapping = pickle.load(map_file)
        current_job_id_mapping[run_id] = {"file_path": path, "cfg": cfg}
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
                num_gpus=NUM_GPUS,
                ag_args_fit={"num_gpus": NUM_GPUS},
            )
        elif data_type == "mm":
            predictor.fit(
                train_data=train_data,
                tuning_data=tuning_data,
                hyperparameters=hyperparameters,
                presets=presets,
                time_limit=time_limit,
            )

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
