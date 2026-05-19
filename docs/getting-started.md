# Getting Started

## Installation

```bash
conda env create -f environment.yml
conda activate cfdUQ
```

## Project Layout

```
scripts/
├── driver/
│   ├── driver_uq.py          # Entry point: run UQ samples
│   └── src/
│       ├── uq.py             # UqDriver orchestration
│       ├── grf_remote.py     # Random field generation (KLE)
│       ├── java_manager.py   # STAR-CCM+ Java macro preparation
│       ├── job_manager.py    # Job submission (local or SLURM)
│       ├── rf_manager.py     # Remote random field management
│       └── config.py         # YAML config reader
├── preprocessor/
│   ├── inputlhsGen/
│   │   └── processor_BEPU_sampling.py   # LHS sample generation
│   └── numericalleastSquare/
│       ├── driver.py                  # Entry point: compute LS fields
│       └── src/
│           └── ls.py                  # FieldLS and LeastSquare classes
├── environment.yml
└── mkdocs.yml
```



## Step-by-Step Workflow
Each run is controlled by a YAML config file. 

### 1. Generate LHS Samples for input error
To generate the random samples using Latin-hypercube approach, run the following command:
```bash
cd preprocessor/inputlhsGen
python processor_BEPU_sampling.py path/to/input/config.yaml

```
The driver `processor_BEPU_sampling.py` generates LHS samples for all uncertain input parameters.
The documentation could be found in [processor_BEPU_sampling.py](api/processor_BEPU_sampling.md).


### 2. Compute Least-Squares Error Fields

```bash
python preprocessor/numericalleastSquare/driver.py config/ls_config.yaml
```

Reads CFD output CSVs across multiple grid resolutions, interpolates onto a common base grid, and fits a least-squares Richardson extrapolation at each point. Outputs `ls_*.json` files (one per spatial point) and a `U.csv` bounds file.

### 3. Run the UQ Driver

Edit `CONFIG_PATH` in `driver/driver_uq.py` to point to your YAML config, then:

```bash
cd driver
python driver_uq.py
```

For each sample ID, the driver:

1. Creates a sample folder under `root/`
2. Copies the `.sim`, ILS, and Java files
3. Injects BEPU parameters into the Java macro
4. Generates a random field (GRF/KLE) remotely
5. Submits the job via SLURM (`EngagingManager`) or runs it locally (`LocalManager`)

## HPC Job Submission

Two backends are available:

| Class | Use case |
|-------|---------|
| `LocalManager` | Run directly in the terminal |
| `EngagingManager` | Submit via SLURM to MIT Engaging cluster |

The active backend is configured in `driver_uq.py`.
