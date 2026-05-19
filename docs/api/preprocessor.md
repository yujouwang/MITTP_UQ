# Preprocessor API

---

## LHS Sampling

Generates Latin Hypercube Samples (LHS) for uncertain input parameters (e.g. mass flow, inlet temperature, material properties) plus mode coefficients (`XI_0`, `XI_1`, ...) and a discretization error random variable (`DEVAR`).

### Usage

```bash
python preprocessor/inputlhsGen/processor_BEPU_sampling.py path/to/config.yaml
```

### Config format

```yaml
path:
  save_to: files/input_error/lhs_samples.csv

model_error:
  N_modes: 20          # number of KLE mode coefficients (XI_0 ... XI_19)

input_error:
  MASSFLOW:
    mean: 1.3096
    std: 0.01
  TIN:
    mean: 508.56
    std: 1.0
```

The output CSV has one row per sample and columns: `SampleID`, all input parameters, `DEVAR`, `XI_0` ... `XI_{N_modes-1}`.

::: preprocessor.inputlhsGen.processor_BEPU_sampling
    options:
      members:
        - lhs_gaussian_independent
        - parse_input_error
        - get_save_path
        - get_n_modes
        - main

---

## Least-Squares Fields

Computes Richardson-extrapolation-based discretization error bounds at every spatial point, using CFD outputs from multiple grid resolutions.

### Usage

```bash
python preprocessor/numericalleastSquare/driver.py path/to/config.yaml
```

### What it does

1. Reads CFD output CSVs for each grid resolution defined in `grid_info_list`
2. Detects coordinate columns automatically (supports `X (m)`, `X (in)`, `X`, `x`, etc.)
3. Sorts all grids by coordinates and validates they share the same spatial points
4. Fits a least-squares model at each point across grid resolutions
5. Outputs `ls_*.json` (one per point) and a `U.csv` with lower/upper bounds

Existing `ls_*.json` files are skipped automatically, so runs can be resumed.

::: preprocessor.numericalleastSquare.src.ls
    options:
      members:
        - get_coordinate_columns
        - get_required_field_column
        - validate_matching_coordinates
        - compute_ls
        - GridInfo
        - FieldLS
        - LeastSquare
