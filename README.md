# OOD AutoML

## Overview

OOD AutoML is an Open OnDemand Batch Connect app that launches an interactive AutoGluon web server session on HPC clusters. It is designed for users who want to run AutoGluon training jobs, review job logs, and run post-training inference through a browser-based workflow without manually wiring together backend APIs.

- Upstream project: [AutoGluon](https://auto.gluon.ai/)

## Screenshots

A screenshot is recommended for deployer verification. This repository currently does not include one; add a site-specific image under `docs/` or `screenshots/`.

<!-- Example once available: -->
<!-- ![Application running in browser](docs/screenshot.png) -->

## Features

- Launches an AutoGluon-backed web server as an Open OnDemand interactive app.
- Supports both CPU and GPU node launches through the OOD form (`node_type`, `num_gpus`, per-node-type walltime and memory).
- Provides a Vue-based UI with pages for:
  - starting training runs,
  - viewing historic jobs and logs,
  - running inference from saved jobs.
- Exposes backend endpoints for server-side file browsing and CSV/Parquet preview to support file picking and inference output inspection.
- Stores historic run metadata under `~/.ood_automl/runs_index.pkl` for later inspection in the UI.

## Requirements

### Compute Node Software

- Python 3.10 (module currently set to `Python/3.10.8`).
- AutoGluon Python package (plus FastAPI/uvicorn stack from `backend/requirements.txt`).
- Site module environment with:
  - `GCC/12.2.0`
  - `Python/3.10.8`
  - `WebProxy`
- Slurm-managed cluster nodes (this app emits Slurm directives in `submit.yml.erb`).
- For GPU mode: access to a GPU partition with `--gres=gpu:<type>:<count>` semantics.

### Open OnDemand

- Open OnDemand with Batch Connect support.
- Scheduler: Slurm.
- Environment Modules/Lmod support (the launch scripts call `module purge` / `module load` and `ml`).

### Optional

- CUDA-capable GPUs for accelerated AutoGluon training.
- Additional sample/user datasets accessible from compute nodes.

## App Installation

Please see the [References section](#software-installation) for software-level installation notes.

### 1. Clone the repository

```bash
cd /var/www/ood/apps/sys
git clone https://github.com/keeganasmith/ood_automl.git
cd ood_automl
# pin to a release/tag if your site requires it
```

### 2. Configure for your site

Update the Batch Connect form and launch scripts to match your cluster:

- `form.yml.erb` for cluster id and user-facing launch options.
- `modules.sh` for local module names and versions.
- `template/script.sh.erb` for site install paths (`CODE_PATH`) and launch behavior.

Key values commonly customized:

| Attribute / Setting | Current value | Change to |
|-----------|---------|-----------|
| `cluster` (`form.yml.erb`) | `"launch"` | Your OOD cluster id |
| CPU/GPU partitions (`submit.yml.erb`) | `cpu` / `gpu` | Your Slurm partition names |
| module stack (`modules.sh`) | `GCC/12.2.0`, `Python/3.10.8`, `WebProxy` | Module names on your site |
| code path (`template/script.sh.erb`) | `/sw/hprc/sw/ood_automl` | Deployed app path at your site |

### 3. Verify

No OOD restart is typically required for Batch Connect app discovery. In the OOD dashboard, verify **AutoGluon** appears under **Interactive Apps > Servers**, launch it, and confirm the app serves at `/node/<host>/<port>/`.

## Configuration

### `form.yml.erb` attributes

| Attribute | Description | Default |
|-----------|-------------|---------|
| `cluster` | Target OOD cluster id | `"launch"` |
| `node_type` | Node class selector (`CPU` or `a30`) | `CPU` |
| `num_gpus` | Number of GPUs requested for GPU node type | `1` |
| `cpu_num_hours` | CPU job walltime (hours) | `1` |
| `gpu_num_hours` | GPU job walltime (hours) | `1` |
| `num_cores` | Requested task/core count | `1` |
| `cpu_total_memory` | CPU job memory (GB) | `1` |
| `gpu_total_memory` | GPU job memory (GB) | `1` |
| `bc_account` | Optional scheduler account | empty |
| `email` | Optional email for Slurm notifications | empty |

### Scheduler mapping (`submit.yml.erb`)

- Always sets:
  - `--ntasks=<num_cores>`
  - `--ntasks-per-node=<num_cores>`
- CPU mode sets:
  - `--partition=cpu`
  - `--time=<cpu_num_hours>:00:00`
  - memory from CPU memory form value
- GPU mode sets:
  - `--gres=gpu:<node_type>:<num_gpus>`
  - `--partition=gpu`
  - `--time=<gpu_num_hours>:00:00`
  - memory from GPU memory form value
- If `email` is set, it adds `--mail-type=ALL` and `--mail-user=<email>`.

### Runtime environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BASE_URL` | No | Prefix used by FastAPI routes behind `/node/<host>/<port>` proxying. |
| `NO_PROXY`, `no_proxy` | Set by default | Excludes loopback from proxy routing. |

## Troubleshooting

### Job starts but app does not open

1. Check the Batch Connect output and `server.log` in the backend directory.
2. Verify modules load cleanly (`module purge`, then module loads from `modules.sh`).
3. Confirm `CODE_PATH` in `template/script.sh.erb` points to the deployed app.
4. Ensure uvicorn is available in the active environment.

### "Module not found" errors

The module names in `modules.sh` or site-specific environment differ from your cluster. Replace them with local equivalents.

### Connection timeout

- Confirm the compute node can bind and expose the selected port.
- Validate that the web process starts (`python3 -m uvicorn app:app ...`).
- Increase expected startup time if the Python environment is cold.

## Testing

Current repository test assets indicate pytest-based backend tests:

| Scope | Command | Status |
|------|---------|--------|
| Backend tests | `backend/run_tests.sh` | Available in repo |

Suggested deployment verification:

1. Launch app with default CPU settings.
2. Confirm the UI loads and websocket connection succeeds.
3. Start a small training run using a sample dataset.
4. Open **Jobs** and **Job Logs** pages to verify run indexing.
5. Run inference with an output CSV path and confirm preview rows render.

## Known Limitations

- Several launch settings are currently site-specific (for example, cluster id, module names, and hardcoded `CODE_PATH`) and must be edited for non-LAUNCH deployments.
- The README examples in the frontend are generic Vue template docs and do not describe production deployment.
- Repository includes generated/minified `form.js`, making hand edits difficult unless source workflow is documented.

## Contributing

Contributions are welcome.

1. Fork this repository.
2. Create a branch (`git checkout -b feature/my-improvement`).
3. Submit a pull request describing your change and validation steps.

For bugs and feature requests, open an issue in this repository.

This app is part of the [OOD Appverse](https://ondemand.connectci.org/affinity-groups/ood-appverse).

## References

- [AutoGluon](https://auto.gluon.ai/) — machine learning framework used by this app.
- [Open OnDemand](https://openondemand.org/) — HPC portal framework used to launch this Batch Connect app.

### Software Installation

You can provide site-specific software build instructions here (or in a separate markdown file), for example:

- How AutoGluon is installed (module, virtualenv, or container).
- How the backend Python environment is built from `backend/requirements.txt`.
- Any GPU/runtime prerequisites.
- Paths that must exist on compute nodes (`CODE_PATH`, scratch locations, dataset mounts).

## License

[MIT License](LICENSE.txt)

## Acknowledgments

Originally adapted from Open OnDemand app patterns maintained by the Ohio Supercomputer Center and extended by project contributors.
