import re
from typing import Dict, Any, List, Optional, Tuple

def _search(pattern: str, text: str, flags=re.MULTILINE | re.DOTALL) -> Optional[re.Match]:
    return re.search(pattern, text, flags)

def _findall(pattern: str, text: str, flags=re.MULTILINE | re.DOTALL) -> List[Tuple[str, ...]]:
    return re.findall(pattern, text, flags)
from typing import List, Dict, Any, Optional

def format_models(models: List[Dict[str, Any]], top: Optional[int] = None) -> str:
    """
    Format a list of AutoGluon model dicts into a readable multiline string.

    - Sorts by score (desc) when available.
    - Shows metric, train/val runtimes, basic resources, and ensemble weights if present.
    - `top` limits how many entries are included (after sorting).

    Returns a single string.
    """
    if not models:
        return ""

    # Sort by score desc when present; keep original order for ties/missing
    def _score_key(m: Dict[str, Any]):
        s = m.get("score")
        return (s is not None, s if isinstance(s, (int, float)) else float("-inf"))
    sorted_models = models

    if top is not None and top > 0:
        sorted_models = sorted_models[:top]

    lines = []
    lines.append("Validation models:")
    for m in sorted_models:
        name = str(m.get("name", ""))
        score = m.get("score")
        metric = m.get("metric")
        train_rt = m.get("train_runtime_s")
        val_rt = m.get("val_runtime_s")
        resources = m.get("resources") or {}
        extra = m.get("extra") or {}

        # Pieces
        score_str = f"{score:.4f}" if isinstance(score, (int, float)) else ""
        metric_str = f" ({metric})" if metric else ""

        rt_parts = []
        if isinstance(train_rt, (int, float)):
            rt_parts.append(f"train {train_rt:.2f}s")
        if isinstance(val_rt, (int, float)):
            rt_parts.append(f"val {val_rt:.2f}s")
        rt_str = ", ".join(rt_parts)

        res_parts = []
        if "cpus" in resources:
            res_parts.append(f"cpus={resources['cpus']}")
        if "gpus" in resources:
            res_parts.append(f"gpus={resources['gpus']}")
        if "mem_used_gb" in resources and "mem_avail_gb" in resources:
            res_parts.append(f"mem={resources['mem_used_gb']}/{resources['mem_avail_gb']} GB")
        res_str = " ".join(res_parts)

        extra_parts = []
        ew = extra.get("ensemble_weights")
        if ew:
            extra_parts.append(f"weights={ew}")
        extra_str = ", ".join(extra_parts)

        # Assemble line without nested f-strings
        line = f"• {name}: {score_str}{metric_str}"
        if rt_str:
            line += f" — {rt_str}"
        if res_str:
            line += f" — {res_str}"
        if extra_str:
            line += f" — {extra_str}"

        lines.append(line)

    return "".join(lines)

def one_is_none(variables: list[Any]):
    for variable in variables:
        if variable is None:
            return True
    return False

def parse_autogluon_log(log_text: str) -> Dict[str, Any]:
    """
    Parse an AutoGluon Tabular log (even if incomplete) and produce a structured dict
    with a human-readable summary under ['summary'].

    Returns:
        {
          'system': {...},
          'presets': {...},
          'paths': {...},
          'dataset': {...},
          'problem': {...},
          'featuregen': {...},
          'eval': {...},
          'split': {...},
          'models': [ {name, score, metric, train_runtime_s, val_runtime_s, resources, extra}, ... ],
          'best_model': {...} or None,
          'runtime': {...},
          'notes': [...],
          'summary': "..."
        }
    """
    t = log_text or ""
    data: Dict[str, Any] = {
        'system': {},
        'presets': {},
        'paths': {},
        'dataset': {},
        'problem': {},
        'featuregen': {},
        'eval': {},
        'split': {},
        'models': [],
        'best_model': None,
        'runtime': {},
        'notes': []
    }

    # --- System Info block ---
    sys_block = _search(r"=+ System Info =+\n(?P<body>.+?)\n=+",
                        t)
    if sys_block:
        body = sys_block.group("body")
        for line in body.strip().splitlines():
            m = _search(r"^\s*([^:]+):\s+(.*)$", line)
            if m:
                key = m.group(1).strip()
                val = m.group(2).strip()
                data['system'][key] = val

    # --- Presets & hyperparameters preset ---
    m = _search(r"Preset alias specified:\s*'([^']+)'\s+maps to\s+'([^']+)'", t)
    if m:
        data['presets']['alias'] = m.group(1)
        data['presets']['alias_maps_to'] = m.group(2)
    m = _search(r"Presets specified:\s*(\[[^\]]*\])", t)
    if m:
        data['presets']['specified'] = m.group(1)
    m = _search(r"Using hyperparameters preset:\s*hyperparameters='([^']+)'", t)
    if m:
        data['presets']['hyperparameters'] = m.group(1)

    # --- Save path ---
    m = _search(r'AutoGluon will save models to\s+"([^"]+)"', t)
    if m:
        data['paths']['model_dir'] = m.group(1)

    # --- Dataset stats ---
    m = _search(r"Train Data Rows:\s*(\d+)", t);  data['dataset']['rows'] = int(m.group(1)) if m else None
    m = _search(r"Train Data Columns:\s*(\d+)", t);  data['dataset']['cols'] = int(m.group(1)) if m else None
    m = _search(r"Label Column:\s*([^\n]+)", t);  data['dataset']['label'] = m.group(1).strip() if m else None

    # --- Problem type & labels ---
    m = _search(r"Problem Type:\s*([^\n]+)", t)
    if m:
        data['problem']['type'] = m.group(1).strip()
    m = _search(r"AutoGluon will gauge predictive performance using evaluation metric:\s*'([^']+)'", t)
    if m:
        data['eval']['metric'] = m.group(1)

    # --- Split info ---
    m = _search(r"Automatically generating train/validation split with holdout_frac=([0-9.]+),\s*Train Rows:\s*(\d+),\s*Val Rows:\s*(\d+)", t)
    if m:
        data['split'] = {
            'holdout_frac': float(m.group(1)),
            'train_rows': int(m.group(2)),
            'val_rows': int(m.group(3)),
        }

    # --- Feature generation summary (counts) ---
    m = _search(r"(\d+)\s+features in original data used to generate\s+(\d+)\s+features in processed data", t)
    if m:
        data['featuregen']['original_features'] = int(m.group(1))
        data['featuregen']['processed_features'] = int(m.group(2))
    m = _search(r"Train Data \(Processed\) Memory Usage:\s*([0-9.]+)\s*MB", t)
    if m:
        data['featuregen']['processed_mem_mb'] = float(m.group(1))

    # --- Model fit sections ---
    # Pattern captures model blocks even if truncated.
    # Start with "Fitting model: NAME ..." and greedily take until next "Fitting model:" or end.
    model_blocks = _findall(r"(Fitting model:\s*([^\s.]+)\s*\.\.\.[\s\S]*?)(?=^Fitting model:|\Z)", t)
    for full_block, model_name in model_blocks:
        # Basic fields
        resources = {}
        m = _search(r"Fitting with cpus=(\d+),\s*gpus=(\d+)(?:,\s*mem=([0-9.]+)/([0-9.]+)\s*GB)?", full_block)
        if m:
            resources = {
                'cpus': int(m.group(1)),
                'gpus': int(m.group(2)),
            }
            if m.group(3) and m.group(4):
                resources.update({'mem_used_gb': float(m.group(3)), 'mem_avail_gb': float(m.group(4))})

        # Score & metric (may be missing if incomplete)
        score = None; metric = None
        m = _search(r"([0-9.]+)\s*=\s*Validation score\s*\(([^)]+)\)", full_block)
        if m:
            score = float(m.group(1)); metric = m.group(2).strip()

        # Runtimes
        train_rt = None; val_rt = None
        m = _search(r"([0-9.]+)s\s*=\s*Training\s+runtime", full_block)
        if m:
            train_rt = float(m.group(1))
        m = _search(r"([0-9.]+)s\s*=\s*Validation\s+runtime", full_block)
        if m:
            val_rt = float(m.group(1))

        # Extra notes (ensembles, weights, etc.)
        extra = {}
        m = _search(r"Ensemble Weights:\s*({[^}]+})", full_block)
        if m:
            extra['ensemble_weights'] = m.group(1)

        if((not one_is_none([train_rt, score, metric])) and resources != {}):
            data['models'].append({
                'name': model_name,
                'score': score,
                'metric': metric,
                'train_runtime_s': train_rt,
                'val_runtime_s': val_rt,
                'resources': resources or None,
                'extra': extra or None,
            })

    # --- Best model, throughput, total runtime ---
    m = _search(r"training complete, total runtime\s*=\s*([0-9.]+)s.*?Best model:\s*([^\|]+?)\s*\|\s*Estimated inference throughput:\s*([0-9.]+)\s*rows/s\s*\((\d+)\s*batch size\)",
                t)
    if m:
        data['runtime']['total_runtime_s'] = float(m.group(1))
        data['best_model'] = {'name': m.group(2).strip()}
        data['runtime']['throughput_rows_per_s'] = float(m.group(3))
        data['runtime']['batch_size'] = int(m.group(4))
    else:
        # If not present, try to at least infer a best model by max score among parsed models
        scored = [m for m in data['models'] if m.get('score') is not None]
        if scored:
            best = max(scored, key=lambda x: x['score'])
            data['best_model'] = {'name': best['name'], 'inferred': True, 'score': best['score']}
            data['notes'].append("Best model inferred from available scores (training may be incomplete).")

    # --- Predictor save path (if present) ---
    m = _search(r'TabularPredictor saved.*?load\("([^"]+)"\)', t)
    if m:
        data['paths']['predictor_load_path'] = m.group(1)

    # --- Decision threshold calibration note (keep as a note if present) ---
    m = _search(r"Disabling decision threshold calibration.*", t)
    if m:
        data['notes'].append(m.group(0).strip())

    # --- Build human-readable summary ---
    def fmt(x, default="?"):
        return default if x is None else str(x)

    metric = data['eval'].get('metric')
    rows = data['dataset'].get('rows')
    cols = data['dataset'].get('cols')
    label = data['dataset'].get('label')
    prob = data['problem'].get('type')
    tr = data['split'].get('train_rows')
    vr = data['split'].get('val_rows')
    total_rt = data['runtime'].get('total_runtime_s')
    save_dir = data['paths'].get('model_dir')
    best_name = data['best_model']['name'] if data['best_model'] else None

    # Top models by score (if any)
    top_lines = []
    scored_models = [m for m in data['models'] if m.get('score') is not None]
    scored_models.sort(key=lambda m: m['score'], reverse=True)
    for m in scored_models[:5]:
        metric_str = f" ({m['metric']})" if m.get('metric') else ""
        train_str  = f", train {m['train_runtime_s']}s" if m.get('train_runtime_s') is not None else ""
        val_str    = f", val {m['val_runtime_s']}s"     if m.get('val_runtime_s')   is not None else ""
        top_lines.append(f"• {m['name']}: {m['score']:.4f}{metric_str}{train_str}{val_str}")

    summary_parts = []
    summary_parts.append("AutoGluon Tabular run summary")
    if rows or cols or label or prob:
        summary_parts.append(f"- Dataset: {fmt(rows)} rows, {fmt(cols)} cols | label='{fmt(label)}' | problem={fmt(prob)}")
    if tr or vr or metric:
        summary_parts.append(f"- Split: train={fmt(tr)} | val={fmt(vr)} | metric={fmt(metric)}")
    fg = data.get('featuregen', {})
    if fg.get('original_features') is not None:
        processed = fg.get('processed_features', '?')
        mem_mb = fg.get('processed_mem_mb')
        mem_str = f", processed mem ~{mem_mb} MB" if mem_mb is not None else ""
        summary_parts.append(
            f"- Features: {fg['original_features']} → {processed} processed{mem_str}"
            )
    if top_lines:
        summary_parts.append("- Validation scores (top):\n  " + "\n  ".join(top_lines))
    if best_name:
        summary_parts.append(f"- Best model: {best_name}")
    if total_rt is not None:
        summary_parts.append(f"- Total training runtime: {total_rt}s")
    if save_dir:
        summary_parts.append(f"- Models saved to: {save_dir}")
    rt = data.get('runtime', {})
    thr = rt.get('throughput_rows_per_s')
    if thr is not None:  # use None-check so 0.0 wouldn't be skipped
        batch = rt.get('batch_size')
        batch_str = f" @ batch {batch}" if batch is not None else ""
        summary_parts.append(
            f"- Inference throughput (est): {thr} rows/s{batch_str}"
        )
    if data['notes']:
        summary_parts.append("- Notes:\n  " + "\n  ".join(f"• {n}" for n in data['notes']))

    data['summary'] = "\n".join(summary_parts)
    data["models"] = format_models(data["models"])
    return data


# Example usage:
if __name__ == "__main__":
    
    with open("./autogluon_runs/e6169d252e9f44dab2b90d7bb5821ada/logs/predictor_log.txt", "r") as file:
        SAMPLE = file.read()
    result = parse_autogluon_log(SAMPLE)
    #print(result['summary'])
    # Access structured pieces:
    print(result['models'])
    #print(result['system'])
