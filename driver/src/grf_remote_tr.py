"""Transient variant of grf_remote.py: KL modes are tracked across windows.

Called as `python grf.py <window>` by the transient macro
(template_java_tr2.java) once per perturbation window. The xi of a sample are
fixed, but the covariance is rebuilt from the current ILS each window, so the
eigenvectors change and xi_j would otherwise land on a different spatial
pattern every window. Here every new mode is matched to the previous mode it
overlaps most (searching +-ALIGN_BAND sorted positions around where that mode
sat last window) and its sign is set to agree with it, so xi_j stays attached
to the same, slowly evolving, mode j - as U_prev does in ref_tr_java.java,
plus re-matching when modes swap order.

  python grf.py        identical to grf_remote.py; no state read or written
                       (the pre-launch call in the slurm script)
  python grf.py 0      fresh start: ignores any old state, writes KLE_STATE
  python grf.py k>0    aligns to KLE_STATE, then overwrites it

Modes inside a group of (near-)equal eigenvalues have no unique identity, so
the match there is best effort; the log reports how well modes were tracked.
"""
import json
import csv
import os
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import scipy
from scipy import special
from scipy.spatial import distance_matrix, cKDTree

import logging
logger = logging.getLogger(__name__)

# Previous window's tracked modes (float32 V, n x n) and where each tracked
# mode sat in the eigenvalue-sorted order. Written next to grf.py.
KLE_STATE = 'kle_state.npz'

# How many sorted positions a mode may move between two windows and still be
# matched to its previous self.
ALIGN_BAND = 50


def _normalized_column_name(column):
    return column.strip().lower()


def _extract_unit(column):
    """Return the unit string from 'X (m)' → 'm', or '' if no unit is present."""
    normalized = _normalized_column_name(column)
    if '(' in normalized and normalized.endswith(')'):
        return normalized[normalized.index('(') + 1:-1].strip()
    return ''


def find_coordinate_columns(df):
    coord_columns = {}
    for axis in ('x', 'y', 'z'):
        matches = [
            column for column in df.columns
            if _normalized_column_name(column) == axis
            or _normalized_column_name(column).startswith(f'{axis} (')
        ]
        if not matches:
            raise KeyError(
                f"Could not find coordinate column for '{axis.upper()}'. "
                f"Expected labels like '{axis.upper()} (m)' or '{axis.upper()}' (SI, meters). "
                f"Available columns: {list(df.columns)}"
            )
        col = matches[0]
        unit = _extract_unit(col)
        if unit not in ('', 'm'):
            raise ValueError(
                f"Coordinate column '{col}' has unit '{unit}'. "
                f"Only SI units are accepted (meters). "
                f"Please convert coordinates to meters before loading."
            )
        coord_columns[axis] = col
    return [coord_columns[axis] for axis in ('x', 'y', 'z')]


class MultiplierBepu:
    def __init__(self, target_quantity, k_l0, s_2, ils_filepath, de_filepath, bepu_input_dict, save_to, model_error_on, disc_error_on, ils_norm=None, cov_form='mean'):
        self.k_l0 = k_l0
        self.s_2 = s_2
        # ils_norm: None keeps the length scale k_l0 * ILS in meters; a dict
        # {l_ref, ils_ref, l_min_factor} normalizes it, see get_length_scale()
        self.ils_norm = ils_norm
        # cov_form: 'mean' (arithmetic mean of the pointwise length scales) or
        # 'paciorek' (Paciorek-Schervish, positive semi-definite by construction)
        assert cov_form in ('mean', 'paciorek'), f'Unknown cov_form: {cov_form}'
        self.cov_form = cov_form
        self.ils_filepath = Path(ils_filepath)
        if de_filepath:
            self.de_filepath = Path(de_filepath)
        else:
            self.de_filepath = None
        self.target_quantity = target_quantity
        self.bepu_input_dict = bepu_input_dict
        self.save_to = Path(save_to)
        self.save_to.mkdir(parents=True, exist_ok=True)

        self.filepaths = {
            'cov_matrix': self.save_to/'cov_matrix.csv',
            'V': self.save_to/'V.csv',
            'D': self.save_to/'D.csv',
            'modes': self.save_to/'modes'
        }

        self.ils_me = None
        self.ils_de = None
        self.ils_ie = None
        self.ils_base, self.coord, self.coord_columns = self.init_ils()
        self.model_error_on = model_error_on
        self.disc_error_on = disc_error_on
        if self.ils_norm is not None:
            self.init_ils_norm()

    def init_ils_norm(self):
        """Fix the normalization constants from the base ILS.

        ils_ref comes from ils_base, never from the per-sample total ILS, so the
        discretization-error part of the ILS still changes the length scale.
        """
        norm = self.ils_norm
        assert 'l_ref' in norm, 'ils_norm needs l_ref (m).'
        self.l_ref = float(norm['l_ref'])

        ils_ref = norm.get('ils_ref', 'median')
        if ils_ref == 'median':
            self.ils_ref = float(np.median(self.ils_base))
        elif ils_ref == 'mean':
            self.ils_ref = float(np.mean(self.ils_base))
        else:
            self.ils_ref = float(ils_ref)
        assert self.ils_ref > 0, f'ils_ref must be positive, got {self.ils_ref}'

        # Nearest-neighbour spacing of the RF points, for the length-scale floor
        self.l_min_factor = float(norm.get('l_min_factor', 0.0))
        self.h = cKDTree(self.coord).query(self.coord, k=2)[0][:, 1]
        logger.info(f'ILS normalization: l_ref={self.l_ref}, ils_ref={self.ils_ref:.4e}, '
                    f'l_min_factor={self.l_min_factor}')
        return

    def init_ils(self) :
        # Read data
        logger.debug('Get ils: Reading data')
        ils_df = pd.read_csv(self.ils_filepath)
        coord_columns = find_coordinate_columns(ils_df)
        ils_df.sort_values(by=coord_columns, inplace=True, ignore_index=True)
        coord = ils_df[coord_columns].to_numpy()
        ils_base = ils_df[self.target_quantity].to_numpy()
        return ils_base, coord, coord_columns

    def compute_ils_me(self):
        """
        ILS for model error
        """
        logger.debug('Compute model error of ILS')
        if self.model_error_on:
            self.ils_me =  self.ils_base  # example: 10% of the base ILS
        else:
            print(f'Model error off')
            self.ils_me = np.zeros_like(self.ils_base)
        return


    def compute_ils_de(self, rv):
        if self.disc_error_on:
            logger.info('Compute random ils of DE')
            assert self.de_filepath.exists(), f'{self.de_filepath} not found.'
            
            # # Get bounds and compute random ILS values with given uncertainty type
            # bounds = np.loadtxt(self.de_filepath, delimiter=',')
            # lb = bounds[:, 0]
            # ub = bounds[:, 1]

            df = pd.read_csv(self.de_filepath)
            coord_columns = find_coordinate_columns(df)
            df.sort_values(by=coord_columns, inplace=True, ignore_index=True)
            lb = df['LB'].values
            ub = df['UB'].values

            if rv > 0:
                ils_rand = + rv/2 * (self.ils_base - ub)
            else:
                ils_rand = + abs(rv)/2 * (self.ils_base - lb)
                
            ils_rand[ils_rand < 0] = 0  # remove negative values
            self.ils_de = ils_rand
        else:
            print(f'Discretization error off')
            self.ils_de = np.zeros_like(self.ils_base) 
        return

    def compute_ils_ie(self):
        """ ILS for input error """
        self.ils_ie = 0
        return 

    def get_cov_matrix_v0(self):
        """Original implementation, kept for reference and cross-checks.

        Uses scipy.special.kn(1, x), the general integer-order routine,
        which is ~5x slower than the k1(x) specialization used by
        get_cov_matrix(). Values agree to ~2e-15 relative.
        """
        logger.debug('Covariance matrix not found. Running process_cov_matrix')
        ils =  self.ils_me + self.ils_de + self.ils_ie
        coord = self.coord

        n = coord.shape[0]
        r  = distance_matrix(coord, coord, p=2)
        ils_mean = np.add.outer(ils, ils) / 2

        # avoid division by zero: 
        ils_mean[ils_mean<1E-9] = 1E-9


        r_l0 = r / (self.k_l0*ils_mean)*2
        g = scipy.special.gamma(1)

        C = np.zeros((n, n))
        C = self.s_2/ g * np.sqrt(2) * r_l0 * scipy.special.kn(1, np.sqrt(2) * r_l0)
        c = self.s_2 / g* np.sqrt(2)
        np.fill_diagonal(C, c)
        np.savetxt(self.filepaths['cov_matrix'], C, delimiter=",")
        return C
 

    # Above this Bessel argument, u * K1(u) is below machine epsilon relative
    # to the diagonal (u=40 -> 3.4e-17 against a diagonal of ~1.75), so the
    # entry is zero in double precision. The threshold is dimensionless and
    # independent of s_2 / k_l0, which scale diagonal and off-diagonal alike.
    BESSEL_CUTOFF = 40.0

    def get_length_scale(self, ils):
        """Pointwise length scale L_i entering the covariance (u = 2 sqrt(2) r / L).

        Without ils_norm, L_i = k_l0 * ILS_i in meters, as in v0. With ils_norm
        the ILS only sets the spatial shape and l_ref sets the size:

            L_i = k_l0 * l_ref * ILS_i / ils_ref

        so k_l0 is dimensionless (L = k_l0 * l_ref where ILS = ils_ref). L_i is
        then floored at l_min_factor * (nearest-neighbour spacing at i), so
        low-ILS regions (near walls) do not fall below the point spacing and
        turn into uncorrelated noise.
        """
        if self.ils_norm is None:
            return self.k_l0 * ils

        L = self.k_l0 * self.l_ref * ils / self.ils_ref
        if self.l_min_factor > 0:
            L_min = self.l_min_factor * self.h
            n_floored = int(np.count_nonzero(L < L_min))
            L = np.maximum(L, L_min)
            logger.info(f'Length scale floor applied at {n_floored}/{len(L)} points')
        q = np.percentile(L, [0, 50, 100])
        logger.info(f'Length scale L (m): min {q[0]:.3e}, median {q[1]:.3e}, max {q[2]:.3e}')
        return L

    def get_cov_matrix(self):
        """Matern nu=1 covariance with a pointwise-varying length scale.

        With cov_form='mean' this agrees with get_cov_matrix_v0() to ~6e-16
        absolute (eigenvalues to ~3e-14), but evaluates the Bessel function
        only where it is not numerically zero. On this case's data the
        correlation length is far below the point spacing, so ~0.1% of the
        n x n entries survive the cutoff and the build is ~8-11x faster than
        the dense kn(1, .) form.

        Averaging L_i and L_j arithmetically does not give a valid covariance
        when L varies in space: with a sharp near-wall drop in ILS the matrix
        has large negative eigenvalues, which get_kle() then clips. The
        Paciorek-Schervish form (cov_form='paciorek', d=3),

            L_ij^2 = (L_i^2 + L_j^2) / 2
            C_ij   = (L_i L_j / L_ij^2)^(3/2) * s_2/g * u K1(u),  u = 2 sqrt(2) r / L_ij

        is positive semi-definite for any L field and equals 'mean' when L is
        uniform.
        """
        logger.debug('Covariance matrix not found. Running process_cov_matrix')
        ils = self.ils_me + self.ils_de + self.ils_ie
        coord = self.coord
        L = self.get_length_scale(ils)

        r = distance_matrix(coord, coord, p=2)
        # avoid division by zero: same floor as v0, 1E-9 on the averaged ILS
        L_floor = self.k_l0 * 1E-9
        if self.cov_form == 'paciorek':
            L_ij = np.add.outer(L**2, L**2)
            L_ij /= 2
            np.maximum(L_ij, L_floor**2, out=L_ij)
            pre = np.multiply.outer(L, L)
            pre /= L_ij
            pre **= 1.5
            np.sqrt(L_ij, out=L_ij)
        else:
            L_ij = np.add.outer(L, L)
            L_ij /= 2
            np.maximum(L_ij, L_floor, out=L_ij)

        g = scipy.special.gamma(1)

        # The Bessel argument u = sqrt(2) * r_l0 equals the prefactor, so
        # C = s_2/g * u * K1(u). Built in place to avoid n x n temporaries.
        u = r
        u /= L_ij
        u *= 2               # u is now r_l0
        u *= np.sqrt(2)      # u is now sqrt(2) * r_l0
        del L_ij

        C = np.zeros_like(u)
        near = u < self.BESSEL_CUTOFF
        # k1(0) is inf and inf * 0 is nan on the diagonal; overwritten by
        # fill_diagonal below, exactly as in v0.
        with np.errstate(invalid='ignore'):
            C[near] = (self.s_2 / g) * scipy.special.k1(u[near]) * u[near]
        if self.cov_form == 'paciorek':
            C[near] *= pre[near]
            del pre

        c = self.s_2 / g* np.sqrt(2)
        np.fill_diagonal(C, c)
        np.savetxt(self.filepaths['cov_matrix'], C, delimiter=",")
        return C

    def get_de_rv(self):
        de_rv =  self.bepu_input_dict['DEVAR']
        logger.debug(f'de_rv value: {de_rv}')
        return float(de_rv)
    
    def get_xi_coeffs(self, n_truncate):
        return np.array([float(self.bepu_input_dict[f'XI_{i}']) for i in range(n_truncate)])  # minus DEVAR

    
    def align_to_previous(self, V, D, V_prev, pos_prev):
        """Reorder and re-sign the sorted modes (V, D) to follow V_prev.

        Returns (V, D, pos): column j of the returned V is the new mode matched
        to previous tracked mode j, and pos[j] is its eigenvalue-sorted index.
        """
        n = V.shape[1]

        # M[j, k] = <previous tracked mode j, new sorted mode k>
        M = V_prev.T @ V.astype(np.float32)
        absM = np.abs(M)

        # Candidate pairs: new sorted modes within ALIGN_BAND of the slot that
        # tracked mode j held last window. Greedy, best overlap first.
        offsets = np.arange(-ALIGN_BAND, ALIGN_BAND + 1)
        cand_k = pos_prev[:, None] + offsets[None, :]
        valid = (cand_k >= 0) & (cand_k < n)
        cand_j = np.broadcast_to(np.arange(n)[:, None], cand_k.shape)[valid]
        cand_k = cand_k[valid]
        score = absM[cand_j, cand_k]

        match = np.full(n, -1, dtype=np.int64)
        taken = np.zeros(n, dtype=bool)
        for idx in np.argsort(-score, kind='stable'):
            j = cand_j[idx]
            k = cand_k[idx]
            if match[j] < 0 and not taken[k]:
                match[j] = k
                taken[k] = True

        # Anything the band could not place: pair leftovers in sorted order.
        left_j = np.where(match < 0)[0]
        if left_j.size:
            left_j = left_j[np.argsort(pos_prev[left_j], kind='stable')]
            match[left_j] = np.where(~taken)[0]
            logger.warning(f'Mode tracking: {left_j.size} mode(s) had no match '
                           f'within +-{ALIGN_BAND} positions; paired in order.')

        rows = np.arange(n)
        V = V[:, match]
        D = D[match]
        signs = np.sign(M[rows, match])
        signs[signs == 0] = 1.0
        V *= signs

        overlap = absM[rows, match]
        energy = D / D.sum() if D.sum() > 0 else np.full(n, 1.0 / n)
        n_moved = int(np.count_nonzero(match != pos_prev))
        n_flipped = int(np.count_nonzero(signs < 0))
        logger.info(f'Mode tracking: variance-weighted overlap '
                    f'{float(energy @ overlap):.4f}; median overlap '
                    f'{float(np.median(overlap)):.4f}; {n_moved} mode(s) changed '
                    f'sorted position, {n_flipped} sign flip(s) undone.')
        print(f'Mode tracking: variance-weighted overlap {float(energy @ overlap):.4f}, '
              f'median {float(np.median(overlap)):.4f}, moved {n_moved}, flipped {n_flipped}')

        return V, D, match

    def track_modes(self, V, D, window):
        """Apply mode tracking for perturbation window `window` (None: off)."""
        if window is None:
            return V, D

        state_path = self.save_to / KLE_STATE
        n = V.shape[1]
        pos = np.arange(n)

        if window > 0 and state_path.exists():
            state = np.load(state_path)
            V_prev = state['V']
            pos_prev = state['pos']
            if V_prev.shape == V.shape:
                V, D, pos = self.align_to_previous(V, D, V_prev, pos_prev)
            else:
                logger.warning(f'{state_path} holds {V_prev.shape} modes, '
                               f'expected {V.shape}; starting tracking afresh.')
            del state, V_prev
        elif window > 0:
            logger.warning(f'{state_path} not found at window {window}; '
                           f'starting tracking afresh.')

        # Write through a temporary file so an interrupted save cannot leave a
        # truncated state behind for the next window.
        tmp_path = self.save_to / ('tmp_' + KLE_STATE)
        np.savez(tmp_path, V=V.astype(np.float32), pos=pos)
        os.replace(tmp_path, state_path)
        return V, D

    def get_kle(self, N_truncate, window=None):
        logger.info(f'Get KLE')

        # update ils
        self.compute_ils_me()
        de_rv = self.get_de_rv()
        self.compute_ils_de(rv=de_rv)
        self.compute_ils_ie()

        # Compute the grf 
        C = self.get_cov_matrix()
        n_modes = len(C)
        # C is symmetric positive semi-definite by construction, so its SVD
        # and its eigendecomposition coincide. eigh exploits that symmetry:
        # ~2x faster than svd at n ~ 1e4, with eigenvalues and modes matching
        # to ~1e-8 and the covariance V @ diag(D) @ V.T reproduced exactly.
        # eigh returns ascending eigenvalues, so flip to the descending order
        # that svd returned and that the KLE truncation below assumes.
        w, Q = np.linalg.eigh(C)
        order = np.argsort(w)[::-1]
        D = w[order]
        V = Q[:, order]

        # Round-off can push the trailing eigenvalues of a PSD matrix slightly
        # negative; svd returned magnitudes, so sqrt(D) was always real. Clip
        # to keep that true when N_truncate reaches the numerical null space.
        # A large negative minimum means C itself is not a valid covariance.
        logger.info(f'Smallest eigenvalue before clipping: {D[-1]:.3e} '
                    f'(largest {D[0]:.3e})')
        np.maximum(D, 0.0, out=D)

        # Eigenvector signs are arbitrary (they were with svd too). Pin them
        # with a deterministic convention - largest-magnitude entry positive -
        # so repeated runs with the same xi draw the same field.
        peak = np.abs(V).argmax(axis=0)
        signs = np.sign(V[peak, np.arange(V.shape[1])])
        signs[signs == 0] = 1.0
        V *= signs

        # Keep xi_j on the same mode as last window (no-op when window is None)
        V, D = self.track_modes(V, D, window)

        # Compose rf
        mu = np.zeros((n_modes,1))
        xi_coeffs = self.get_xi_coeffs(N_truncate)
        rf = mu + V[:, :N_truncate] @ (np.diag(np.sqrt(D[:N_truncate])) @xi_coeffs.reshape(-1, 1))
        rf_lognormal = np.exp(np.sqrt(self.s_2)*rf)
        logger.info('Finished generating random field using KLE')

        # Create data framew 
        coord = self.coord
        # Save V and D
        np.savetxt(self.filepaths['V'], V, delimiter=",")
        np.savetxt(self.filepaths['D'], D, delimiter=",")

        # Create a folder, parse the modes V and save them as csv files for visualization
        modes_folder = self.filepaths['modes']
        modes_folder.mkdir(parents=True, exist_ok=True)
        for i in range(20): 
            mode_i = V[:, i]

            df_mode = pd.DataFrame(
                np.concatenate([coord, mode_i.reshape(-1, 1)], axis=1),
                columns=[*self.coord_columns, "mode"]
            )

            out_file = modes_folder / f"mode_{i}.csv"

            with open(out_file, "w") as f:
                f.write('"X (m)","Y (m)","Z (m)",mode\n')

            df_mode.to_csv(
                out_file,
                mode="a",
                index=False,
                header=False
            )


        # df 
        df = pd.DataFrame(np.concatenate([coord, rf_lognormal], axis=1), columns=[*self.coord_columns, 'phi'])
        return df

    def df(self, N_trunc):
        # read data
        filepath = self.filepaths.get(f'rf_trunc{N_trunc}', self.save_to/f'rf_trunc{N_trunc}.csv')
        if filepath.exists() is False:
            raise FileNotFoundError(f'{filepath} not found.')
        else:
            df = pd.read_csv(filepath)
        return df
    
    
    def get_sample(self, N_trunc, sample_id):
        return self.df(N_trunc).iloc[:, sample_id+4].to_numpy()


def write_rf_csv(df, filepath):
    with open(filepath, 'w', newline='') as f:
        header = [f'"{column}"' if column in df.columns[:3] else column for column in df.columns]
        f.write(','.join(header) + '\n')
        df.to_csv(f, index=False, header=False, quoting=csv.QUOTE_MINIMAL)


def read_config(config_path):
    """ Read the config file """
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config


if __name__ == "__main__":

    # Perturbation window index from the transient macro; absent for the
    # pre-launch call, which then behaves exactly like grf_remote.py.
    window = int(sys.argv[1]) if len(sys.argv) > 1 else None

    current_dir = Path(__file__).parent
    config_path = current_dir / 'rf_dict.json'
    bepu_path = current_dir / 'bepu_input_dict.json'
    ils_filepath = current_dir / 'ils.csv'

    var_config = read_config(config_path = config_path)
    target_quantity = var_config['target_quantity']
    k_l0 = float(var_config['k_l0'])
    s_2 = float(var_config['s_2'])
    de_filepath = var_config['de_filepath']
    n_trunc = int(var_config['n_trunc'])

    bepu_input_dict = read_config(bepu_path)

    # Initialize the variables
    m = MultiplierBepu(
        target_quantity = target_quantity,
        k_l0 = k_l0, 
        s_2 = s_2, 
        ils_filepath=ils_filepath, 
        de_filepath = de_filepath,
        bepu_input_dict=bepu_input_dict, 
        model_error_on = var_config['model_error_on'],
        disc_error_on = var_config['disc_error_on'],
        ils_norm = var_config.get('ils_norm'),
        cov_form = var_config.get('cov_form', 'mean'),
        save_to='.')

    # m.get_cov_matrix()
    df = m.get_kle(N_truncate=n_trunc, window=window)

    # Dump the phi as rf.csv
    write_rf_csv(df, 'rf.csv')
