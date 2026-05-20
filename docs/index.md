# MIT-TP Research Scripts

Tools for running **Best Estimate Plus Uncertainty (BEPU)** analysis on CFD simulations (STAR-CCM+). 

## Overview

The workflow has two main stages:

1. **Preprocessor**
   - Input error : Latin-hypercube sampling
   - Numerical error: Least-square estimation
2. **Driver**


## Modules
| Module | Purpose |
|--------|---------|
| [`driver/`](api/driver.md) | UQ runs: sample setup, job submission, random field generation |
| [`preprocessor/inputlhsGen/`](api/processor_BEPU_sampling.md) | Latin Hypercube Sampling for uncertain input parameters |
| [`preprocessor/numericalleastSquare/`](api/processor_leastSquare.md) | Compute least-squares discretization error fields across grid resolutions |


## Tutorial
- See [getting-started](getting-started.md)
- Example: [Demo Elbow](Demo_elbow.md)