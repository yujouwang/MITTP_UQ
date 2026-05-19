
## Estimate the numerical error using least-square approach

Computes least-square version of Richardson-extrapolation-based discretization error bounds at every spatial point, using CFD outputs from multiple grid resolutions.

The workflow is: 
```
Conduct mesh convergence tests for 4 (or more) mesh 
-> STAR-CCM+ output csv files (with columns X, Y, Z, L0) for each mesh configuration
-> The code to read those csv files
-> Perform point-by-point least-square estimation 
```

### Usage

```bash
cd preprocessor/numericalleastSquare
python processor_leastSquare.py path/to/ls_config.yaml
```


## The config file
The configuration file contains information of 
1. The directory
2. The target quantity for error estimation (integral length scale in our case)
3. The file location
4. The mesh configuration (how many cells used in grid convergence study)





```yaml
paths:
  root:  '/path/to/root' # where to save the results  

ls:
  field_name: 'Integral length scale' # the target of the numerical error estimation
  save_to:  '/path/to/results' # where to save the results 

grids:
  grid_1: 
    name: 'grid0' # name of the grid object
    dir: '/path/to/mesh_folder' # where to find the STAR-CCM+ output csv 
    field_file_name: 'ils.csv' # the name of the output csv
    N: 2094751 # number of cells used in this mesh 
    V: 0.01398  # the volume of the target region

  grid_2:
    name: 'grid1'
    dir: '/path/to/mesh_folder' 
    field_file_name: 'ils.csv'
    N: 456351
    V: 0.01398  

  grid_3:
    name: 'grid2'
    dir: '/path/to/mesh_folder'
    field_file_name: 'ils.csv'
    N: 163257
    V: 0.01398  

  grid_4:
    name: 'grid3'
    dir: '/path/to/mesh_folder'
    field_file_name: 'ils.csv'
    N: 237738
    V: 0.01398  

points:  # ask the code to perform point-by-point estimation, start the point id 0, end with point id 3565 
  start: 0 
  end: 3565  
```



After execution, it creates four `U_i` folders  (and a bunch of intermediate files)

```
/path/to/results
├── U_0
│   └── U.csv  # correspond to the error of grid0/ils.csv 
├── U_1
│   └── U.csv  # correspond to the error of grid1/ils.csv 
├── U_2
│   └── U.csv  # correspond to the error of grid2/ils.csv 
└── U_3
    └── U.csv  # correspond to the error of grid3/ils.csv 

```

For each of `U.csv`, it contains information of `(X, Y, Z)` and `LB, UB` (lower bound and upper bound)
