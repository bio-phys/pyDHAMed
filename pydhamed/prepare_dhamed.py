from __future__ import print_function
from six.moves import range

import numpy as np
from collections import defaultdict

def state_lifetimes_counts(transition_count_matrix_l,
                           n, nwin):
    """
    
    Calculate lifetimes in each of the states (for each run/window)
    
    Parameters:
    -----------
    transition_count_matrix_l: list of arrays
        List of arrays with transition count matrices. One array for
        each run/windows. 
    n: int
        Number of (structural) states
    nwin: int
        Number of simulations runs/windows. I.e., how many umbrella
        winodws were run.    

    Returns:
    --------
    t_ar: array_like
        Array, n x nwin, where n is number of states,
        nwin is number of windows with aggregate lifetimes in the states.

    """
    #n = len(transition_count_matrix_l[0][:,0])
    #nwin = len(transition_count_matrix_l)
    t_ar = np.zeros((n,nwin), dtype=np.float64)

    for iwin, win in enumerate(transition_count_matrix_l):
        # sum over the column gives all counts in a state
        t_ar[:, iwin] = np.sum(win, axis=0)
    return t_ar


def total_transition_counts(transition_count_matrix_l, n):
    """
    Parameters:
    -----------
    transition_count_matrix_l: list of arrays

    Returns:
    --------
    nn_ar: array_like, total transitions j->i

    """
    #n = len(transition_count_matrix_l[0][:,0])
    nn_ar = np.zeros((n,n))

    # do j=1,n
    #     do i=1,n
    #        nn(i,j)=0.d0
    #        do iwin=1,nwin
    #           nn(i,j)=nn(i,j)+nij(i,j,iwin)
    #        enddo
    #     enddo

    for j in range(n):
        for i in range(n):
            for iwin, win in enumerate(transition_count_matrix_l):
                nn_ar[i,j] += win[i,j]
    return nn_ar


def counts_in_out(transition_count_matrix_l, n, nwin):
    """
    Parameters:
    -----------
    transition_count_matrix_l: list of arrays
        List of arrays with transition count matrices. One array for
        each run/windows. 
    n: int
        Number of (structural) states
    nwin: int
        Number of simulations runs/windows. I.e., how many umbrella
        winodws were run.    

    Returns:
    --------
    n_in
    n_out

    """
    n_in = np.zeros(n)
    n_out = np.zeros(n)

    #for k in range(n):
    for iwin, count_matrix in enumerate(transition_count_matrix_l):
        for i, row in enumerate(count_matrix):
            for j, col_e in enumerate(row):
                if i != j:
                    n_in[i] += count_matrix[i,j]
                    n_out[i] += count_matrix[j,i]
    return n_in, n_out


def check_transition_pairs(transition_count_matrix_l, n_in, n_out, n_states, t_ar):
    """
    Check if bin/state i is paired at least once, with at least one transition into
    the state and one transition out of the state. Unpaiews states are subsequently
    excluded from the analysis since no proper equilibrium can be established for them.
    
    Parameters:
    -----------
    transition_count_matrix_l: list of arrays
        List of arrays with transition count matrices. One array for
        each run/windows. 
    n_in: array
        Number of transitions into given states.
    n_out: array
        Number of transitions from given state.
    n_states: integer
    t_ar: array_like
        Array with dimension, n x nwin, where n is number of states,
        nwin is number of windows. Contains aggregate  
  
    Returns:
    --------
    paired_ar: array
        Number of transition pairs for each state.
          
    """
    paired_ar = np.zeros(n_states)

    for iwin, count_matrix in enumerate(transition_count_matrix_l):
        for i in range(n_states-1):
            # At least a transition into and out of the state
            if (n_in[i] > 0.0) and (n_out[i] > 0.0):
                for j in range(i+1, n_states):
                    # Transition to/from connected states 
                    if (n_in[j] > 0.0) and (n_out[j] > 0.0):
                       # After checking that equilibrium can be established
                       #check if states paired in this run/window
                        if count_matrix[i,j] + count_matrix[j,i] > 0.0:
                            if t_ar[i,iwin] + t_ar[j,iwin] > 0.0:
                                paired_ar[i] += 1
                                paired_ar[j] += 1
    return paired_ar


def actual_transition_pairs(n_in, n_out, n_states, paired_ar, verbose=False):
    """
    Generate indeces of transition pairs. The indices of transition pairs are
    required to setup the input for the actual optimization of the DHAMed
    effective likelihood.
    
    Parameters:
    -----------
    n_in: array
        Number of transitions into given states
    n_out: array
        Number of transitions from given states
    paired_ar: array
        Number of transition pairs for each state.
    verbose: Boolean
    
    Returns:
    --------
    pair_idx_d: defaultdict
        Indeces of the paired states. Shifts the indices to account for
        excluded, unpaired states.
    n_actual: int
        Actual number of states included in the DHAMed calculation.
    
    """
    n_actual = 0
    pair_idx_d = defaultdict(list)
    # index of included points
    for i in range(n_states):
        if (n_in[i] > 0.0) and (n_out[i] > 0.0) and (paired_ar[i] > 0):

            pair_idx_d[i].append(n_actual)
            n_actual += 1
        else:
            print ("bin {} excluded".format(i))
    if verbose:
       print(n_actual)
    return pair_idx_d, n_actual


def prepare_dhamed_input_pairs(n_states, transition_count_matrix_l,
                               n_in, n_out,
                               paired_ar, t_ar, pair_idx_d,
                               v_ar):
    """
    Parameters:
    -----------
    n_states: integer, number of (conformational) states
    transition_count_matrix_l: list of arrays, transition count matrices
    n_in: array, number of transitions into given states
    n_out: array, number of transitions from given state
    paired_ar: array 
    t_ar: array_like, n x nwin, where n is number of states,
          nwin is number of windows
    pair_idx_d
    v_ar: array, bias potentials

    Returns:
    --------
    dhamed_input_list: list, formatted inputs for DHAMed

    """
    ip_l = []
    jp_l = []
    vi = []
    vj = []
    ti = []
    tj = []
    nijp = []
    n_pair = 0

    for iwin, count_matrix in enumerate(transition_count_matrix_l):
        for i in range(n_states-1):
            # test whether transition in/out of paired states i and j were observed
            if (n_in[i] > 0.0) and (n_out[i] > 0.0) and (paired_ar[i] > 0 ):
                for j in range(i+1, n_states):
                     if (n_in[j] > 0.0) and (n_out[j] > 0.0) and (paired_ar[i] > 0 ):
                            # transition in current window?
                            if count_matrix[i,j] + count_matrix[j,i] > 0:
                                if (t_ar[i, iwin] + t_ar[j, iwin] > 0.0):
                                    # lifetime > 0
                                    n_pair += 1
                                    ip_l.append(pair_idx_d[i][0] + 1)
                                    jp_l.append(pair_idx_d[j][0] + 1)
                                    vi.append(v_ar[i,iwin])
                                    vj.append(v_ar[j,iwin])
                                    ti.append(t_ar[i,iwin])
                                    tj.append(t_ar[j,iwin])
                                    nijp.append( count_matrix[i,j] + count_matrix[j,i])
    print(n_pair)
    return (np.array(ip_l, dtype=int), np.array(jp_l, dtype=int), np.array(vi), np.array(vj), np.array(ti),
            np.array(tj), np.array(nijp))


def generate_dhamed_input(c_l, v_ar, n_states, n_win, return_included_state_indices=True):
    """
    Converts a list of count matrices and an array of bias potentials
    to the input for DHAMed. For efficient calculation DHAMed input data
    is organized into transition pairs.

    Parameters:
    -----------
    c_l: list,
        List of arrays. Each array contains a transition count matrix.
    v_ar: array
        Array of bias potentials
    n_states: int
        Number of states/bins.
    n_win: int
        Number of simulation runs or windows.
    return_included_state_indices: boolean, optional
        Return indices of the states to be included in the calculation.

    Returns:
    --------
    n_out: array like
        N entries, list of total number of transitions out of bin i.
    ip: array_like
        npair entries, list of indices of bin i in transition pair.
    jp: array_like
        npair entries, list of indices of bin j in transition pair.
    vi: array_like
        npair entries, list of potentials in kT units at bin i of a pair.
    ti: array_like
        npair entries, list of residence times in bin i of a pair.
    tj: array like
        npair entries, list of residence times in bin j of a pair.
    nijp: array_like
        npair entries, number of j->i and i->j transitions combined in a pair.
    n_actual: int
        actual number of connected states which can be analyzed.
    included_state_indices: array_like
        Indices of states included in the DHAMed calculation (optional)

    """
    t = state_lifetimes_counts(c_l, n_states, n_win)
    n_in, n_out = counts_in_out(c_l, n_states, n_win)
    pairs = check_transition_pairs(c_l, n_in, n_out, n_states, t)
    pair_idx_d, n_actual = actual_transition_pairs(n_in, n_out, n_states, pairs)
    ip, jp, vi, vj, ti, tj, nijp  = prepare_dhamed_input_pairs(n_states, c_l, n_in, n_out,
                                                               pairs, t, pair_idx_d, v_ar)
    if return_included_state_indices:
       return n_out, ip, jp, vi, vj, ti, tj, nijp, n_actual, pair_idx_d
    else:                                                            
         return n_out, ip, jp, vi, vj, ti, tj, nijp, n_actual
