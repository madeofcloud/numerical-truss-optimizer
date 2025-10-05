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

def calculate_material_cost(stresses_df, materials_df):
    """
    Calculates the total material cost of the truss ($O_m$).
    Currently, this is defined as the total volume ($\sum A_i L_i$) of all members,
    multiplied by a cost factor.
    """
    # FIX: Handle empty DataFrame gracefully
    if stresses_df.empty:
        # If the solver failed, we can't calculate cost, but assume a typical cost
        # or return 0, as the penalty takes care of the score.
        return 0.0
    total_volume = 0.0
    
    # Check if 'cost_per_volume' exists, if not, use a default value
    if 'cost_per_volume' not in materials_df.columns:
        materials_df['cost_per_volume'] = 1.0

    # Ensure materials_df has a 'material_id' column for lookup
    if 'material_id' not in materials_df.columns:
        materials_df['material_id'] = materials_df.index
        
    for _, row in stresses_df.iterrows():
        length = row['L']
        
        # Area 'A' is already on stresses_df from the truss_solver
        area = row.get('A', 0.001)
        
        # Find the correct material row to get the cost
        # The material_id is assumed to be on the stresses_df (passed from truss_analyze)
        material_row = materials_df[materials_df['material_id'] == row.get('material_id', 0)].iloc[0]
        cost_per_volume = material_row.get('cost_per_volume', 1.0)
        
        # Volume = Area * Length
        volume = area * length
        total_volume += volume * cost_per_volume # Total Cost is sum of (Volume * Cost/Volume)
        
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
# 4) Calculate a combined score
# --------------------------
def calculate_all_metrics(data, alpha=5.16e3, lambd=1.0):
    """
    Runs the full analysis and returns a dictionary of all calculated metrics.
    """
    stresses_df, displacements = run_truss_simulation(data)
    
    # Calculate objectives as metrics
    buckling_indices = calculate_buckling_indices(stresses_df, alpha, lambd)
    buckling_penalty_score = calculate_buckling_penalty(stresses_df)
    material_cost_score = calculate_material_cost(stresses_df, data['materials'])
    avg_force_magnitude = calculate_average_force_magnitude(stresses_df)

    metrics = {
        **buckling_indices,
        'buckling_penalty_score': buckling_penalty_score,
        'material_cost_score': material_cost_score,
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
    material_cost_score = metrics['material_cost_score']

    # Compression Uniformity ($O_u$): Coefficient of variation ($\nu_{\mu}$)
    compressive_uniformity_score = metrics['coefficient_of_variation']
    
    # Average Force Magnitude ($O_a$): Average loading magnitude
    avg_force_magnitude_score = metrics['avg_force_magnitude']
    
    # Total Design Score $\Omega$ calculation
    score = (
        buckling_distribution_factor_score * weights['buckling_distribution_factor'] +
        buckling_penalty_score * weights['buckling_penalty'] +
        material_cost_score * weights['material_cost'] +
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