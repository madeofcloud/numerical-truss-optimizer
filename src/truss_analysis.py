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
    stresses_df, displacements = truss_analyze(
        data["points"], data["trusses"], data["supports"], data["materials"], data["loads"]
    )
    return stresses_df, displacements

# --------------------------
# 3) Calculations for buckling indices
# --------------------------
def calculate_buckling_indices(stresses_df, alpha=5.16e3, lambd=1.0):
    """
    Calculates the weighted mean, weighted variance, and safety margin
    based on the buckling utilization ratios.
    (Formulas from SSA 3 research report)
    """
    # Filter for compressive members
    compressive_members = stresses_df[stresses_df['axial_force'] < 0].copy()
    
    if compressive_members.empty:
        return {
            'weighted_mean': 0.0,
            'weighted_variance': 0.0,
            'safety_margin': 0.0,
            'coefficient_of_variation': 0.0
        }

    # Calculate buckling utilization ratio for each compressive member
    compressive_members['mu'] = np.abs(compressive_members['axial_force'] / compressive_members['Pc'])
    
    # Calculate weighted mean (gamma)
    numerator = (compressive_members['mu'] * np.abs(compressive_members['axial_force'])).sum()
    denominator = np.abs(compressive_members['axial_force']).sum()
    gamma = numerator / denominator
    
    # Calculate weighted variance (s_mu^2)
    # The formula from the paper is slightly different, let's use the standard weighted variance
    # s_mu^2 = (sum(w * (x-x_bar)^2)) / sum(w)
    weights = np.abs(compressive_members['axial_force'])
    variance = np.sum(weights * (compressive_members['mu'] - gamma)**2) / np.sum(weights)
    s_mu = np.sqrt(variance)

    # Calculate safety margin and coefficient of variation
    safety_margin = gamma + 2 * s_mu
    v_mu = s_mu / gamma if gamma != 0 else np.inf
    
    return {
        'weighted_mean': gamma,
        'weighted_variance': variance,
        'safety_margin': safety_margin,
        'coefficient_of_variation': v_mu
    }

def calculate_material_cost(stresses_df, materials_df):
    """
    Calculates the total material cost of the truss.
    Currently, this is defined as the total volume of all members.
    Assumes `materials_df` has a 'cost_per_volume' column.
    """
    total_cost = 0.0
    
    # Check if 'cost_per_volume' exists, if not, use a default value
    if 'cost_per_volume' not in materials_df.columns:
        print("Warning: 'cost_per_volume' not found in materials.csv. Assuming 1.0.")
        materials_df['cost_per_volume'] = 1.0

    # Ensure materials_df has a 'material_id' column for lookup
    if 'material_id' not in materials_df.columns:
        materials_df['material_id'] = materials_df.index
        
    for _, row in stresses_df.iterrows():
        length = row['L']
        
        # We need the original truss data to link to material ID
        # For simplicity, we assume A and cost_per_volume are directly on stresses_df
        # This is not ideal but gets the calculation working
        area = row.get('A', 0.001)
        
        # Find the correct material row to get the cost
        material_row = materials_df[materials_df['material_id'] == row.get('material_id', 0)].iloc[0]
        cost_per_volume = material_row.get('cost_per_volume', 1.0)
        
        # Volume = Area * Length
        volume = area * length
        total_cost += volume * cost_per_volume
        
    return total_cost

def calculate_average_force_magnitude(stresses_df):
    """
    Calculates the average magnitude of the axial forces in all truss members.
    """
    if stresses_df.empty:
        return 0.0
    return np.mean(np.abs(stresses_df['axial_force']))


# --------------------------
# 4) Calculate a combined score
# --------------------------
def calculate_all_metrics(data, alpha=5.16e3, lambd=1.0):
    """
    Runs the full analysis and returns a dictionary of all calculated metrics.
    """
    stresses_df, displacements = run_truss_simulation(data)
    
    # Calculate buckling indices
    buckling_indices = calculate_buckling_indices(stresses_df, alpha, lambd)
    
    # Buckling penalty: if any mu >= 1, return a very high value
    buckling_penalty = 0
    compressive_members = stresses_df[stresses_df['axial_force'] < 0]
    if not compressive_members.empty:
        mu = np.abs(compressive_members['axial_force'] / compressive_members['Pc'])
        if np.any(mu >= 1):
            buckling_penalty = 1.0 # A high penalty
    
    # Calculate material cost, passing the stresses_df which contains the length
    material_cost = calculate_material_cost(stresses_df, data['materials'])
    
    # Calculate the new metric: average force magnitude
    avg_force_magnitude = calculate_average_force_magnitude(stresses_df)


    metrics = {
        **buckling_indices,
        'buckling_penalty_score': buckling_penalty,
        'material_cost_score': material_cost,
        'avg_force_magnitude': avg_force_magnitude,
    }
    
    return metrics, stresses_df


def get_objective(data, weights, alpha=5.16e3, lambd=1.0):
    """
    Combines all metrics into a single objective score.
    Returns: float
    """
    metrics, stresses_df = calculate_all_metrics(data, alpha, lambd)
    
    # Define a high penalty for buckling. If any member buckles, the score is enormous.
    buckling_penalty_score = metrics['buckling_penalty_score']
    
    # Get scores for the other objectives
    safety_margin_score = metrics['safety_margin']
    material_cost_score = metrics['material_cost_score']
    avg_force_magnitude_score = metrics['avg_force_magnitude']

    # Combine with weights to get the total objective score.
    score = (
        safety_margin_score * weights['safety_margin'] +
        buckling_penalty_score * weights['buckling_penalty'] +
        material_cost_score * weights['material_cost'] +
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
    # Load from CSVs
    data = load_truss_data(
        "data/design_3/points.csv",
        "data/design_3/trusses.csv",
        "data/design_3/supports.csv",
        "data/design_3/materials.csv",
        loads_csv="data/design_3/loads.csv"
    )

    # Run one simulation to check
    stresses, displacements = run_truss_simulation(data)
    print("Single simulation results:")
    print(stresses)

    # Example of calculating the buckling indices for the initial design
    weights = {
        'safety_margin': 1.0,
        'buckling_penalty': 1000.0,
        'material_cost': 1000.0,
        'average_force_magnitude': 0.1,  # Added new weight
    }
    
    score, metrics, _ = get_objective(data, weights)
    
    print("\nInitial design score and metrics:")
    print(f"Score: {score:.4f}")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"{key}: {value:.4f}")
        else:
            print(f"{key}: {value}")
