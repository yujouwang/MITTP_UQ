from pathlib import Path
from dataclasses import dataclass
from scipy.optimize import least_squares
from scipy.interpolate import griddata
import numpy as np
import pandas as pd
import json
import glob
import os 
from tqdm import tqdm

# =======================================
#       Helper functions
# =======================================
def mon_range(p):
    if p >= 0.5 and p <=2:
        return True
    else:
        return False

def compute_h(N, V):
    """
    Function to obtain h parameter form inputs N, number of cells, w cell width, l cell length
    """
    h= (V/N)**(1/3)
    return h

def compute_2Dh(N, V):
    """
    Function to obtain h parameter form inputs N, number of cells, w cell width, l cell length
    """
    h= (V/N)**(1/2)
    return h

def compute_ls(i, phi, h, save_path):
    print(f'computing {i}')
    ls = LeastSquare(i, phi, h)
    ls.init()
    ls.compute_epsilon()
    ls.compute_Fs()
    ls.compute_U()
    ls.compute_bounds()

    # save 
    ls.save(save_path)
    return 
# =======================================
#     Estimator classes
# =======================================


class S:
    def __init__(self, phi, h, weighted):
        self.phi = np.array(phi)
        self.h = np.array(h)
        self.weighted = weighted    
        self.n_g = len(phi)

        assert self.n_g > 3, f"Now only {self.n_g} grids,  Not enough data points"
        self._init_w()
        self._init_x0()

        self.name = None
        self.std = None
        self.delta = None
        self.phi_fitted = None

    def _init_w(self):
        if self.weighted == False:
            self.w = [1 for i in range(self.n_g)]
            self.nw = [1 for i in range(self.n_g)]
        else:
            sum_of_h = np.sum([1/self.h[j] for j in range(self.n_g)])
            self.w = [ (1/self.h[i]) /sum_of_h for i in range(self.n_g)]
            self.nw = [self.w[i]*(self.n_g+1) for i in range(self.n_g)]
    
    def _init_x0(self):
        raise NotImplementedError
    
    def fit(self):
        roots = least_squares(
            self.fun, 
            x0 = self.x0,
            xtol = 1e-15,
            gtol = 1e-15,
            max_nfev = 10000,
        )
        self.roots = roots
        # print(roots)

        self.std = self.compute_std()
        self.delta = self.compute_delta()
        self.phi_fitted = self.compute_phi_fitted()
        return 
    
    def fun(self):
        raise NotImplementedError

    def compute_std(self):
        raise NotImplementedError
    
    def compute_phi_fitted(self):
        raise NotImplementedError

    def compute_delta(self):
        raise NotImplementedError

class S_RE(S):
    def __init__(self, phi, h, weighted):
        super().__init__(phi, h, weighted)

        if weighted:
            self.name = 'S_RE_w'
        else:
            self.name = 'S_RE'
        
        self.p = None
        self.phi_0 = None
        self.alpha = None

    def _init_x0(self):
        self.x0 = [self.phi[-1], 1, 2]
    
    def fun(self, x0):
        phi_0, alpha, p = x0
        return np.sum([self.w[i]*(self.phi[i] - (phi_0 + alpha* self.h[i]**p) ) **2 for i in range(self.n_g)] )
    
    def compute_std(self):
        self.phi_0, self.alpha, self.p = self.roots.x
        phi_0, alpha, p = self.roots.x
        std = np.sum([ self.nw[i]* ( self.phi[i] - (phi_0 + alpha * self.h[i]**p ) )**2  for i in range(self.n_g) ] ) / (self.n_g - 3)
        return std

    def compute_delta(self):
        phi_0, alpha, p = self.roots.x
        delta = alpha* self.h**p
        return delta
    
    def compute_phi_fitted(self):
        phi_0, alpha, p = self.roots.x
        return phi_0 + self.compute_delta()
    

    
class S_1(S):
    def __init__(self, phi, h, weighted):
        super().__init__(phi, h, weighted)
        if weighted:
            self.name = 'S1_w'
        else:
            self.name = 'S1'

        self.phi_0 = None
        self.alpha = None

    def _init_x0(self):
        self.x0 = [self.phi[-1], 1]
    
    def fun(self, x0):
        phi_0, alpha = x0
        return np.sum([self.w[i]*(self.phi[i] - (phi_0 + alpha* self.h[i]) ) **2 for i in range(self.n_g)] )
    
    def compute_std(self):
        phi_0, alpha = self.roots.x
        self.phi_0, self.alpha = phi_0, alpha
        std = np.sum([ self.nw[i]* ( self.phi[i] - (phi_0 + alpha * self.h[i] ) )**2  for i in range(self.n_g) ] ) / (self.n_g - 3)
        return std

    def compute_delta(self):
        phi_0, alpha = self.roots.x
        delta = alpha* self.h**1
        return delta
    
    def compute_phi_fitted(self):
        phi_0, alpha = self.roots.x
        return phi_0 + self.compute_delta()


    
class S_2(S):
    def __init__(self, phi, h, weighted):
        super().__init__(phi, h, weighted)
        if weighted:
            self.name = 'S2_w'
        else:
            self.name = 'S2'

        self.phi_0 = None
        self.alpha = None

    def _init_x0(self):
        self.x0 = [self.phi[-1], 1]
    
    def fun(self, x0):
        phi_0, alpha = x0
        self.phi_0, self.alpha = phi_0, alpha
        return np.sum([self.w[i]*(self.phi[i] - (phi_0 + alpha* self.h[i]**2) ) **2 for i in range(self.n_g)] )
    
    def compute_std(self):
        phi_0, alpha = self.roots.x
        std = np.sum([ self.nw[i]* ( self.phi[i] - (phi_0 + alpha * self.h[i]**2 ) )**2  for i in range(self.n_g) ] ) / (self.n_g - 3)
        return std

    def compute_delta(self):
        phi_0, alpha = self.roots.x
        delta = alpha* self.h**2
        return delta
    
    def compute_phi_fitted(self):
        phi_0, alpha = self.roots.x
        return phi_0 + self.compute_delta()

    
class S_12(S):
    def __init__(self, phi, h, weighted):
        super().__init__(phi, h, weighted)
        if weighted:
            self.name = 'S12_w'
        else:
            self.name = 'S12'

        self.phi_0 = None
        self.alpha_1 = None
        self.alpha_2 = None

    def _init_x0(self):
        self.x0 = [self.phi[-1], 1, 1] # phi_0, alpha_1, alpha_2
    
    def fun(self, x0):
        phi_0, alpha_1, alpha_2 = x0
        return np.sum([self.w[i]*(self.phi[i] -  (phi_0 + alpha_1* self.h[i] +  alpha_2* self.h[i]**2) ) **2 for i in range(self.n_g)] )
    
    def compute_std(self):
        phi_0, alpha_1, alpha_2 = self.roots.x
        self.phi_0, self.alpha_1, self.alpha_2 = phi_0, alpha_1, alpha_2
        std = np.sum([ self.nw[i]* ( self.phi[i] - (phi_0 +  alpha_1 * self.h[i]**1 + alpha_2 * self.h[i]**2 ) )**2  for i in range(self.n_g) ] ) / (self.n_g - 3)
        return std

    def compute_phi_fitted(self):
        phi_0, alpha_1, alpha_2 = self.roots.x
        return phi_0 + alpha_1 * self.h + alpha_2* self.h**2

    def compute_delta(self):
        phi_0, alpha_1, alpha_2 = self.roots.x
        delta = alpha_1* self.h**1 + alpha_2* self.h**2
        return delta
    
    def compute_phi_fitted(self):
        phi_0, alpha_1, alpha_2 = self.roots.x
        return phi_0 + self.compute_delta()
    


class Roots:
    def __init__(self, x):
        self.x = np.array(x)
        return


class LeastSquare:
    def __init__(self, i, phi, h):
        self.i = i
        self.phi = phi
        self.h = h

        self.p = None
        self.S = None
        self.epsilon = None
        self.U = None
        self.Fs = None
        return 

    def init(self):
        phi = self.phi

        self.s_re = S_RE(self.phi, self.h, weighted=False)
        self.s_re_w = S_RE(self.phi, self.h, weighted=True)
        self.s_1 = S_1(self.phi, self.h, weighted=False)
        self.s_1_w = S_1(self.phi, self.h, weighted=True)
        self.s_2 = S_2(self.phi, self.h, weighted=False)
        self.s_2_w = S_2(self.phi, self.h, weighted=True)
        self.s_12 = S_12(self.phi, self.h, weighted=False)
        self.s_12_w = S_12(self.phi, self.h, weighted=True)

        self.n_g = len(phi)
        self.init_p()
        self.init_delta_phi()

    def init_p(self):
        print('Start initialize p')
        self.s_re.fit()
        self.s_re_w.fit()
    
    def init_delta_phi(self):
        print('Start initialize delta_phi')
        delta_phi = (np.max(self.phi) - np.min(self.phi)) / (self.n_g - 1)
        self.delta_phi = delta_phi

    def compute_epsilon(self):
        
        p_re  = self.s_re.roots.x[2]
        p_re_w = self.s_re_w.roots.x[2]
        std_re = self.s_re.std
        std_re_w = self.s_re_w.std

        if ( mon_range(p_re) and mon_range(p_re_w) ):
            print('Both p are in the range, find the best one based on std')

            if std_re < std_re_w:
                print(f'Non_weighted wins: p_re = {p_re}, std = {std_re}')
                self.S = self.s_re
                self.p = p_re
                self.epsilon = self.S.compute_delta()

            else:
                print(f'Weighted wins: p_re_w = {p_re_w}, std = {std_re}')
                self.S = self.s_re_w
                self.p = p_re_w
                self.epsilon = self.S.compute_delta()

        elif ( mon_range(p_re)):
            print(f'Non-weighted RE is in the range: p_re = {p_re}, std = {std_re}')
            self.S = self.s_re
            self.p = p_re
            self.epsilon = self.S.compute_delta()
        
        elif ( mon_range(p_re_w)):
            print(f'Weighted RE is in the range: p_re_w = {p_re_w}, std = {std_re_w}')
            self.S = self.s_re_w
            self.p = p_re_w
            self.epsilon = self.S.compute_delta()
        else: 
            print('None of the p is in the range, compute all six std')
            s_list = [self.s_1, self.s_1_w, self.s_2, self.s_2_w, self.s_12, self.s_12_w]
            for s in s_list:
                print(s.name)
                s.fit()

            i_mean = np.argmin([s.std for s in s_list])
            self.S = s_list[i_mean]
            
            self.p = max( p_re, p_re_w)
            self.epsilon = self.S.compute_delta()
            print(f'p = {self.p}, std = {self.S.std}')
        return
    
    def compute_Fs(self):
        std = self.S.std
        if self.p >= 0.5 and self.p <= 2:
            if std  <= self.delta_phi:
                self.Fs = 1.25
            else:
                self.Fs = 3
        else:
            self.Fs = 3
        return 
        
    def compute_U(self):
        std = self.S.std
        phi_fitted = self.S.phi_fitted

        if std < self.delta_phi:
            self.U = self.Fs * self.epsilon +  std  + np.abs(self.phi - phi_fitted)
        else:
            self.U = 3* std / self.delta_phi * ( self.epsilon + std + np.abs(self.phi - phi_fitted) )
        return
    
    def compute_bounds(self):
        lower_bound = self.phi - self.U
        upper_bound = self.phi + self.U
        bounds = list(zip(lower_bound, upper_bound))
        self. bounds = np.array(bounds)
        return 
    
    def save(self, save_to_folder):
        data = {
            'grid_i': self.i,
            'p': self.p,
            'epsilon': self.epsilon.tolist(),
            'Fs': self.Fs,
            'U': self.U.tolist(),
            'bounds': self.bounds.tolist(),
            'delta_phi': self.delta_phi,

            # Save the S object
            'S': {
                'name': self.S.name,
                'phi': self.S.phi.tolist(),
                'h': self.S.h.tolist(),
                'weighted': self.S.weighted,
                'phi_fitted': self.S.phi_fitted.tolist(),
                'std': self.S.std,
                'delta': self.S.delta.tolist(),
                'roots': self.S.roots.x.tolist(),
            }
        }


        # writhe the dictionaly to a json file
        save_to = save_to_folder / f'ls_{self.i}.json'
        if Path(save_to).exists() is False:
            # create 
            with open(save_to, 'w') as f:
                f.write(json.dumps(data) + '\n') 
        # else:
        #     with open(save_to, 'a') as f:
        #         f.write(json.dumps(data) + '\n') 
        return data
    
    def load(self, data):
        self.p = data['p']
        self.epsilon = np.array(data['epsilon'])
        self.Fs = data['Fs']
        self.U = np.array(data['U'])
        self.bounds = np.array(data['bounds'])
        self.delta_phi = data['delta_phi']

        # Load the S object
        S_type = data['S']['name']
        phi = np.array(data['S']['phi'])
        h = np.array(data['S']['h'])
        weighted = data['S']['weighted']   


        if 'S_RE' in S_type:
            self.S = S_RE(phi, h, weighted)
        elif 'S1' in S_type:
            self.S = S_1(phi, h, weighted)
        elif 'S2' in S_type:
            self.S = S_2(phi, h, weighted)
        elif 'S12' in S_type:
            self.S = S_12(phi, h, weighted)
        else:
            raise ValueError(f"Unknown S type: {S_type}")
        
        self.S.phi_fitted = np.array(data['S']['phi_fitted'])
        self.S.std = data['S']['std']
        self.S.delta = np.array(data['S']['delta'])
        self.S.roots = Roots(data['S']['roots'])
        self.phi = self.S.phi
        return
    
    def post_process(self):
        #if the data range delta_phi is too small, then sigma/delta_ph is meaningless
        if self.delta_phi < 1e-6:
            self.U = self.Fs * self.epsilon +  self.S.std  + np.abs(self.S.phi - self.S.phi_fitted)
            self.compute_bounds()

# =======================================
#       Data classes for the grid information
# =======================================
    

@dataclass
class GridInfo:
    name: str
    dir: Path # path to the data 
    N: int # number of cells
    V: float # volume of the domain
    field_file_name: str #e.g., ils.csv

    def __post_init__(self):
        self.h = compute_h(self.N, self.V)
        self.field_file_path = self.dir / self.field_file_name



# =======================================
#       Classes  
# =======================================
    
class FieldLS:
    def __init__(self, grid_info_list, field_name, save_ls_to):
        self.grid_info_list = grid_info_list
        self.field_name = field_name
        self.save_ls_to = save_ls_to

        self.N_g =  len(grid_info_list)
        self.N_points = None
        self._data = None
        self._field_ls = None
        self.coord = {'x': None, 'y': None, 'z': None}
        self._bounds = None
        self._phi = None
    
    @property
    def data(self):
        return self._data
    
    @property
    def field_ls(self):
        return self._field_ls
    
    @property
    def bounds(self):
        return self._bounds
    
    @property
    def phi(self):
        return self._phi

    def collect_data(self):
        # Read the field data from the grid_info_list
        print('Start collecting data')


        # Obtain the grid information based on the first file
        grid_info = self.grid_info_list[0]
        field_file_path = grid_info.field_file_path
        df_base = pd.read_csv(field_file_path)
        df_base.sort_values(by=['X (m)', 'Y (m)', 'Z (m)'], inplace=True, ignore_index=True)
        print(f'Collecting coordinates based on {grid_info.name}')
        print(f'Base grid number: {len(df_base)}')
        self.coord['x'] = df_base['X (m)'].values
        self.coord['y'] = df_base['Y (m)'].values
        self.coord['z'] = df_base['Z (m)'].values


        # Get data  by interpolation
        xi = df_base[['X (m)', 'Y (m)', 'Z (m)']].values  # interpolation point
        data = []
        for grid_info in self.grid_info_list:
            field_file_path = grid_info.field_file_path
            df = pd.read_csv(field_file_path)
            print(f'{grid_info.name} grid number: {len(df)}')

            df.sort_values(by=['X (m)', 'Y (m)', 'Z (m)'], inplace=True, ignore_index=True)
            values = df[self.field_name]
            points = df[['X (m)', 'Y (m)', 'Z (m)']].values
            interp_values = griddata(points, values, xi, method='linear')
            data.append(interp_values)


        data = np.array(data).T
        self._data = data
        print('Data collected')

        # Collect the coordinates
        print('Coordinates collected')
        return 

    
    def compute_field_ls(self, parallel, points_idx=None):
        hs = [grid_info.h for grid_info in self.grid_info_list]
        save_folder = self.save_ls_to
        if points_idx is None:
            points_idx = range(self.N_points)

        if parallel:
            import multiprocessing as mp
            n_proc = mp.cpu_count()
            print(f'Number of cpu: {n_proc}')
            inputs = [(i, self._data[i, :], hs, save_folder) for i in points_idx]
            pool = mp.Pool(processes=n_proc)
            pool.starmap(compute_ls, inputs)
        else:
            for i in range(self.N_points):
                compute_ls(i, self._data[i, :], hs, save_folder)
        return
    
    def read_field_ls(self):
        print('Reading field ls')
        load_from_folder = self.save_ls_to

        files = glob.glob1(load_from_folder, '*.json')

        data = []
        for file in files:
            load_file = load_from_folder / file
            with open(load_file, 'r') as f:
                for line in f:
                    data.append(json.loads(line.strip()) )


        # dicts = [json.loads(json_str) for json_str in json_strings]
        LS = {}
        for d in data:
            i = d['grid_i']
            ls = LeastSquare(i, None, None)
            ls.load(d)
            ls.post_process()
            LS[i] = ls  

        self._field_ls = LS
        self.N_points = len(LS)

    
    def compute_bounds(self, grid_id=None):
        if grid_id == None:
            # choose the h grid 
            grid_id = np.where([grid_info.name == 'h' for grid_info in self.grid_info_list])[0][0]
    
        bounds = np.array([self.field_ls[i].bounds[grid_id, :] for i in range(self.N_points)])
        self._bounds = bounds
        self._phi = self._data[:, grid_id]


        # save bounds 
        save_to = self.save_ls_to / f'U_{grid_id}'
        save_to.mkdir(parents=True, exist_ok=True)
        save_to = save_to / f'U.csv'

        df = pd.DataFrame(
            {'X':self.coord['x'], 
            'Y':self.coord['y'],
            'Z':self.coord['z'], 
            'LB':bounds[:, 0],
            'UB':bounds[:, 1],
            }
        )

        # np.savetxt(save_to, bounds, delimiter=',')
        df.to_csv(save_to, index=False)
        return 
    
