import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from truss_solver import truss_analyze
from math import pi

# --------------------------
# 1) Load CSVs
# --------------------------
def load_truss_data(points_csv, trusses_csv, supports_csv, materials_csv, loads_csv=None):
    """Load truss data from CSV files into DataFrames."""
    data = {
        "points": pd.read_csv(points_csv),
        "trusses": pd.read_csv(trusses_csv),
        "supports": pd.read_csv(supports_csv),
        "materials": pd.read_csv(materials_csv),
        "loads": pd.read_csv(loads_csv) if loads_csv else None
    }
    return data


# --------------------------
# 2) Run one truss simulation
# --------------------------
def run_truss_simulation(data):
    """Run one truss simulation with current node positions."""
    try:
        stresses_df, displacements = truss_analyze(
            data["points"], data["trusses"], data["supports"], data["materials"], data["loads"]
        )
    except Exception as e:
        # If the solver fails (e.g., singular matrix), return empty dataframes.
        # This will be handled in get_objective to give a high penalty.
        print(f"Truss solver failed: {e}")
        return pd.DataFrame(), pd.DataFrame() 

    return stresses_df, displacements

def calculate_original_member_lengths(points_df, trusses_df):
    """
    Calculate the original (undeformed) length of each truss member.
    Returns a pandas Series with length for each element in trusses_df.
    """
    lengths = []
    node_coords = points_df.set_index('Node')[['x', 'y']]

    for _, row in trusses_df.iterrows():
        n1, n2 = row['start'], row['end']
        p1 = node_coords.loc[n1].values
        p2 = node_coords.loc[n2].values
        L0 = np.linalg.norm(p2 - p1)
        lengths.append(L0)

    return pd.Series(lengths, index=trusses_df.index)

# --------------------------
# 3) Calculations for buckling indices and other metrics
# --------------------------
def calculate_buckling_indices(stresses_df, alpha=5.16e3, lambd=1.0):
    """
    Calculates the weighted mean, weighted variance, buckling distribution factor $O_d$,
    and coefficient of variation ($\nu_{\mu}$) for Compression Uniformity.
    """
    # Filter for compressive members
    compressive_members = stresses_df[stresses_df['axial_force'] < 0].copy()
    
    if compressive_members.empty:
        return {
            'weighted_mean': 0.0,
            'weighted_variance': 0.0,
            'buckling_distribution_factor': 0.0,
            'coefficient_of_variation': 0.0
        }

    # Calculate buckling utilization ratio for each compressive member
    compressive_members['mu'] = np.abs(compressive_members['axial_force'] / compressive_members['Pc'])
    
    # Calculate weighted mean (gamma)
    # The SSA defines gamma as the weighted average of the utilization ratio mu_i
    numerator = (compressive_members['mu'] * np.abs(compressive_members['axial_force'])).sum()
    denominator = np.abs(compressive_members['axial_force']).sum()
    gamma = numerator / denominator
    
    # Calculate weighted standard deviation (s_mu)
    weights = np.abs(compressive_members['axial_force'])
    variance = np.sum(weights * (compressive_members['mu'] - gamma)**2) / np.sum(weights)
    s_mu = np.sqrt(variance)

    # [cite_start]Buckling Distribution Factor $O_d$: $\Gamma=\gamma+2s_{\mu}$ (or 'buckling_distribution_factor' in the code) [cite: 238, 261]
    buckling_distribution_factor = gamma + 2 * s_mu 
    
    # Compression Uniformity $O_u$: $O_{u}=\nu_{\mu}=s_{\mu}/\gamma$ (SSA uses $\gamma s_{\mu}$, but $\nu_{\mu}=s_{\mu}/\gamma$ is the standard coefficient of variation)
    # Sticking to $\nu_{\mu}=s_{\mu}/\gamma$ as defined in the code's comments and to avoid compounding with $\gamma$ from the $O_d$ term.
    v_mu = s_mu / gamma if gamma != 0 else np.inf
    
    return {
        'weighted_mean': gamma,
        'weighted_std_dev': s_mu,
        'buckling_distribution_factor': buckling_distribution_factor, # $O_d$
        'coefficient_of_variation': v_mu # Used for $O_u$
    }

def calculate_material_usage(A, L):
    """
    Calculates total material usage ($O_m = \sum A_i L_i$) of all members.
    """    
    # Volume = Area * Length for each member
    total_volume = (A * L).sum()
    
    return total_volume

def calculate_buckling_penalty(stresses_df):
    """
    Calculates the Buckling Failure Penalty ($O_b$).
    A hard limit that acts as a penalty if $\mu_i \ge 1$.
    The code's initial structure uses a simple 1.0 penalty if $\mu \ge 1$.
    """
    # FIX: Handle empty DataFrame gracefully
    if stresses_df.empty:
        return 1e6 # Return a very large penalty if the solver failed
    compressive_members = stresses_df[stresses_df['axial_force'] < 0]
    if not compressive_members.empty:
        # Calculate buckling utilization ratio $\mu_i = T_i / P_{c,i}$
        mu = np.abs(compressive_members['axial_force'] / compressive_members['Pc'])
        
        # [cite_start]The SSA suggests a piecewise exponential function for $\mu_i \ge 0.95$[cite: 278],
        # but the original code uses a simple check for $\mu_i \ge 1$ for a hard penalty.
        # Sticking to the hard penalty structure for compatibility with the existing GUI slider logic
        # which treats it as a large, fixed weight.
        if np.any(mu >= 1):
            return 100.0 # A high base penalty before applying the weight
    return 0.0

def calculate_average_force_magnitude(stresses_df):
    """
    Calculates the Average Magnitude of Internal Forces ($O_a$).
    $O_{a}=\frac{1}{n}\sum_{i=1}^{k}|T_{i}|$
    """
    if stresses_df.empty:
        return 0.0
    # $T_i$ is the axial_force
    return np.mean(np.abs(stresses_df['axial_force']))


# --------------------------
# 4) Normalize metrics to [0, 1] which are on higher orders of magnitude
# --------------------------

def normalized_material_usage(stresses_df, original_lengths):
    """
    Normalize material usage O_m = sum(A_i*L_i) dynamically.
    """
    if stresses_df.empty:
        return 0.0
    
    usage = calculate_material_usage(stresses_df['A'], stresses_df['L'])
    max_usage = calculate_material_usage(stresses_df['A'], original_lengths)
    return usage / max_usage if max_usage != 0 else 0.0


def normalized_average_force(stresses_df, original_forces):
    """
    Normalize average internal force magnitude to [0,1] using the maximum force in the current truss.
    """
    if stresses_df.empty:
        return 0.0
    
    avg_force = calculate_average_force_magnitude(stresses_df)
    
    # Use maximum absolute force among members as dynamic scaling
    # max_force = stresses_df['axial_force'].abs().max()
    max_force = np.mean(original_forces.abs()) if not original_forces.empty else 0.0
    if max_force == 0:
        return 0.0
    
    return avg_force / max_force


# --------------------------
# 5) Calculate a combined score
# --------------------------
def calculate_all_metrics(data, alpha=5.16e3, lambd=1.0):
    """
    Runs the full analysis and returns a dictionary of all calculated metrics.
    """
    stresses_df, displacements = run_truss_simulation(data)
    
    # Calculate objectives as metrics
    buckling_indices = calculate_buckling_indices(stresses_df, alpha, lambd)
    buckling_penalty_score = calculate_buckling_penalty(stresses_df)
    if "original_lengths" not in data or data["original_lengths"] is None:
        data["original_lengths"] = calculate_original_member_lengths(data["points"], data["trusses"])
    material_usage_score = normalized_material_usage(stresses_df, data["original_lengths"])
    avg_force_magnitude = normalized_average_force(stresses_df, data["original_forces"])

    metrics = {
        **buckling_indices,
        'buckling_penalty_score': buckling_penalty_score,
        'material_usage_score': material_usage_score,
        'avg_force_magnitude': avg_force_magnitude,
    }
    
    return metrics, stresses_df


def get_objective(data, weights, alpha=5.16e3, lambd=1.0):
    """
    Combines all metrics into a single objective score (Total Design Score $\Omega$).
    Returns: float
    """
    metrics, stresses_df = calculate_all_metrics(data, alpha, lambd)
    
    # Get scores for the objectives
    # Buckling Distribution Factor ($O_d$): Buckling distribution factor
    buckling_distribution_factor_score = metrics['buckling_distribution_factor']
    
    # Buckling Penalty ($O_b$): Buckling failure penalty
    buckling_penalty_score = metrics['buckling_penalty_score']
    
    # Material Cost ($O_m$): Material consumption
    material_usage_score = metrics['material_usage_score']

    # Compression Uniformity ($O_u$): Coefficient of variation ($\nu_{\mu}$)
    compressive_uniformity_score = metrics['coefficient_of_variation']
    
    # Average Force Magnitude ($O_a$): Average loading magnitude
    avg_force_magnitude_score = metrics['avg_force_magnitude']
    
    # Total Design Score $\Omega$ calculation
    score = (
        buckling_distribution_factor_score * weights['buckling_distribution_factor'] +
        buckling_penalty_score * weights['buckling_penalty'] +
        material_usage_score * weights['material_usage'] +
        compressive_uniformity_score * weights['compressive_uniformity'] +
        avg_force_magnitude_score * weights['average_force_magnitude']
    )
    
    # Ensure the score is a scalar float
    if isinstance(score, np.ndarray):
        score = score.item()

    return score, metrics, stresses_df


# --------------------------
# Example usage in __main__
# --------------------------
if __name__ == "__main__":
    # Example loading part has been omitted for brevity in this response
    pass