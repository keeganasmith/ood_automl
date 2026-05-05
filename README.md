# OOD AutoML

## Overview

OOD AutoML is an Open OnDemand Batch Connect app that launches an interactive AutoGluon web server session on HPC clusters. It is designed for HPC users (researchers, students, and staff) who need a browser-based workflow to configure AutoGluon runs, monitor training logs, and run post-training inference without manually managing services or scripts.

The app launches a FastAPI backend and a Vue frontend within a Batch Connect job and supports tabular, multimodal, time series, and segmentation training workflows through the same interface.

- Upstream project: [AutoGluon](https://auto.gluon.ai)

## Screenshots

![Application running in browser](docs/screenshot.png)

## Features

- Launches an AutoGluon-backed web application as an Open OnDemand interactive app on compute nodes.
- Supports both CPU and GPU execution with launch-time controls for node type, GPU count, wall time, cores, and memory.
- Provides a web UI for:
  - starting new training runs,
  - monitoring streaming training events/logs,
  - browsing and deleting historic jobs,
  - viewing per-job logs,
  - running inference and previewing generated outputs.
- Supports multiple AutoGluon data modalities from one interface:
  - tabular,
  - multimodal,
  - time series,
  - semantic segmentation.
- Persists run metadata for later inspection in `~/.ood_automl/runs_index.pkl`.
- Uses module-based software environments and a Python virtual environment activation flow.

## Requirements

### Compute Node Software

- Python 3.10+ (repository currently loads `Python/3.10.8`).
- AutoGluon (tabular, multimodal, and time series components used by backend code).
- Python dependencies from `backend/requirements.txt` (including FastAPI, uvicorn, pytest stack, and async libraries).
- Environment Modules/Lmod with site module names configured in `modules.sh`.
- Slurm compute environment for Batch Connect job execution.
- Optional but recommended for acceleration:
  - CUDA-capable GPUs,
  - GPU-capable AutoGluon/PyTorch runtime.
- OS tested assumptions appear Linux/HPC-oriented (module environment, Slurm, and shell launch scripts).

### Open OnDemand

- Open OnDemand with Batch Connect support.
- Scheduler: Slurm (the app emits Slurm-native directives in `submit.yml.erb`).
- OOD app deployment under the system app path (for example `/var/www/ood/apps/sys`).

### Optional

- Additional sample or production datasets accessible on compute nodes.
- TensorBoard runtime (the backend includes a tensorboard launch endpoint).

## App Installation

Please see the [References section](#software-installation) below for instructions on how to install the software launched by this app.

### 1. Clone the repository

```bash
cd /var/www/ood/apps/sys
git clone https://github.com/keeganasmith/ood_automl.git
cd ood_automl

# Pin to a release/tag if your site requires change control
# git checkout <tag>
```

### 2. Configure for your site

#### `form.yml.erb` Attributes

Edit `form.yml.erb` and update these values for your cluster:

| Attribute | Description | Default |
|-----------|-------------|---------|
| `cluster` | Target OOD cluster ID | `"launch"` |
| `node_type` | Node profile (`CPU` or `a30`) | `"CPU"` |
| `num_gpus` | Number of GPUs for GPU node type | `1` |
| `cpu_num_hours` | CPU wall time (hours) | `1` |
| `gpu_num_hours` | GPU wall time (hours) | `1` |
| `num_cores` | Number of tasks/cores | `1` |
| `cpu_total_memory` | CPU memory (GB) | `1` |
| `gpu_total_memory` | GPU memory (GB) | `1` |
| `bc_account` | Scheduler account | optional |
| `email` | Email for scheduler notifications | optional |

#### `manifest.yml` Attributes

Edit `manifest.yml` and update these values for your organization:

| Attribute | Change to |
|-----------|-----------|
| `name` | App name shown in OOD UI |
| `category` / `subcategory` | Your preferred OOD menu placement |
| `description` | Site-specific deployment notes and links |

#### Additional site-specific files

Update these files for your environment:

| File | Purpose |
|------|---------|
| `submit.yml.erb` | Slurm directives (partition, gres, memory, walltime, mail options) |
| `modules.sh` | Site module names and proxy-related environment variables |
| `template/script.sh.erb` | Runtime launch behavior, `CODE_PATH`, venv activation, backend startup |

#### Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `BASE_URL` | Set at launch script | Prefix used by FastAPI endpoints under OOD `/node/<host>/<port>/` proxy |
| `NO_PROXY`, `no_proxy` | Recommended | Excludes localhost interfaces from proxy interception |
| `CODE_PATH` | Yes | Absolute path to deployed application used by launch script |

### 3. Verify

No OOD restart is needed (Batch Connect apps are discovered automatically). Visit your OOD dashboard and look for **AutoGluon** under **Interactive Apps > Servers**, then:

1. Launch with default CPU settings.
2. Confirm the app opens successfully in browser.
3. Start a small training run using a known CSV dataset.
4. Confirm events stream in the **Run** page.
5. Open **Jobs** and **Job Logs** and verify the run is indexed.
6. Run inference against the produced model path and confirm output preview appears.

## Troubleshooting

### Job starts but app doesn't appear

1. Check Batch Connect output and backend `server.log`.
2. Verify `CODE_PATH` in `template/script.sh.erb` points to the deployed repo.
3. Verify module commands in `modules.sh` are valid on your cluster.
4. Confirm the virtual environment exists at `${CODE_PATH}/venv` and contains uvicorn/FastAPI dependencies.

### "Module not found" error

The module names in `modules.sh` do not match your site. Run `module spider <name>` and update `modules.sh` accordingly.

### Connection timeout

- Confirm compute nodes can bind/listen on the selected port.
- Check whether environment initialization or Python import time is delaying startup.
- Confirm the backend command launches (`python3 -m uvicorn app:app --host 0.0.0.0 --port <port>`).

### Slurm memory flag mismatch

`submit.yml.erb` currently references `cpu_total_mem` and `gpu_total_mem` while `form.yml.erb` defines `cpu_total_memory` and `gpu_total_memory`. If jobs fail due to missing variables, align these names in your site deployment.

## Testing

| Site | OOD Version | Scheduler | Status |
|------|-------------|-----------|--------|
| Texas A&M LAUNCH (as implied by defaults) | Not specified in repo | Slurm | Configured by default values/scripts |

To verify your installation:

1. Launch the app with default values in OOD.
2. Start a tabular training run from a CSV path.
3. Confirm job metadata appears in `/historic_jobs` and in the Jobs page.
4. Open logs for the job and verify streaming log updates.
5. Run inference and confirm output CSV preview renders.

## Known Limitations

- Single-run policy: backend enforces at most one active training run per app process.
- Several defaults are site-specific (`cluster: launch`, hardcoded `CODE_PATH`, and module names).
- TensorBoard launch path construction appears incomplete and may require fixes before production use.
- README validation matrix is not extensive across multiple OOD/OS combinations.

## Contributing

Contributions are welcome. To contribute:

1. Fork this repository.
2. Create a feature branch (`git checkout -b feature/my-improvement`).
3. Submit a pull request with a clear description and validation steps.

For bugs or feature requests, open an issue in this repository.

This app is part of the [OOD Appverse](https://ondemand.connectci.org/affinity-groups/ood-appverse). Join the [Appverse Affinity Group](https://ondemand.connectci.org/affinity-groups/ood-appverse) to connect with other contributors.

## References

- [AutoGluon](https://auto.gluon.ai/) — machine learning framework launched and orchestrated by this app.
- [Open OnDemand](https://openondemand.org/) — HPC portal framework used for app delivery.

### Software Installation

You can install the underlying software stack using either module-based or virtual-environment workflows:

- Provide site modules required by `modules.sh` (compiler toolchain, Python, proxy module as needed).
- Create and maintain a Python virtual environment at `${CODE_PATH}/venv`.
- Install backend dependencies from `backend/requirements.txt`.
- Install AutoGluon with extras needed for the modalities you plan to support:
  - tabular,
  - multimodal,
  - timeseries.
- If using GPU, ensure compatible CUDA, NVIDIA drivers, and PyTorch/AutoGluon GPU builds.
- Ensure training and inference datasets are readable from compute nodes where Batch Connect jobs execute.

If your software installation documentation is extensive, move it into a dedicated markdown file and link it here.

## License

[MIT License](LICENSE.txt)

## Acknowledgments

Originally adapted from Open OnDemand app patterns and extended by project contributors.
