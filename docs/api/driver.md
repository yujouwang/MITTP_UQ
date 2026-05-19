# Driver API

The driver module orchestrates end-to-end UQ runs: setting up sample folders, preparing simulation files, generating random fields, and submitting jobs.

---

## UQ Orchestration (`uq.py`)

`UqDriver` is the base class. `UqDriverStageRun` is the concrete implementation for stage-run workflows.

For each sample, the flow is:

```
init_sample_folder(sample_id)
  → prepare_sample_files(sample_id)   # copy sim, ILS, exe, Java, slurm, RF files
    → run_sample(sample_id)           # submit job
```

::: driver.src.uq
    options:
      members:
        - optional_path
        - prepare_sim
        - prepare_ils
        - prepare_exe
        - parse_the_bepu_input_var_into_dict
        - UqDriver
        - UqDriverStageRun

---

## Random Field Generation (`grf_remote.py`)

Generates spatially correlated random fields using the **Karhunen-Loève Expansion (KLE)**. The covariance model is a Matérn-type kernel parameterized by `k_l0` (length scale multiplier) and `s_2` (variance).

Three error sources are combined into the ILS (Integral Length Scale):

- **Model error** (`ils_me`): based on the base ILS field
- **Discretization error** (`ils_de`): driven by the `DEVAR` random variable and bounds from a `U.csv` file
- **Input error** (`ils_ie`): currently set to zero

::: driver.src.grf_remote
    options:
      members:
        - find_coordinate_columns
        - write_rf_csv
        - MultiplierBepu

---

## Java File Preparation (`java_manager.py`)

Prepares STAR-CCM+ Java macro files by substituting keywords and BEPU input parameters via string replacement.

::: driver.src.java_manager
    options:
      members:
        - JavaManager
        - JavaUqBepuStageRun

---

## Job Submission (`job_manager.py`)

Abstracts local and SLURM-based job submission. Both managers populate a SLURM/bash template by replacing placeholder tokens (e.g. `SIM_FILE_NAME`, `JAVA_NAME`, `N_CORES_FOR_COMPUTING`).

::: driver.src.job_manager
    options:
      members:
        - JobManager
        - LocalManager
        - EngagingManager

---

## Remote RF Manager (`rf_manager.py`)

Stages all files needed for remote random field generation: copies the GRF script, writes `rf_dict.json` and `bepu_input_dict.json` into each sample folder.

::: driver.src.rf_manager
    options:
      members:
        - RfManagerBepuRemote

---

## Config (`config.py`)

::: driver.src.config
    options:
      members:
        - read_config_from_yaml
