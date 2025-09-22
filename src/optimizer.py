import numpy as np
import pandas as pd
from scipy.optimize import minimize
from truss_analysis import get_objective

def optimize_truss(data, nodes_to_optimize, weights):
    """
    Optimizes the node positions of a truss to minimize a combined objective score.
    
    Args:
        data (dict): Dictionary containing pandas DataFrames for points, trusses, etc.
        nodes_to_optimize (list): List of node IDs to optimize.
        weights (dict): A dictionary of weights for the different objectives.

    Returns:
        A tuple containing:
        - The optimized data dictionary.
        - The final objective function value.
        - The final metrics dictionary.
    """
    # Create a copy of the data to modify
    current_data = data.copy()

    # Get the initial positions of the nodes to optimize
    # The nodes_to_optimize list contains node IDs, so we need to map them to the DataFrame index
    # We use .loc[] for label-based indexing
    initial_positions = current_data["points"].set_index('Node').loc[nodes_to_optimize, ['x', 'y']].values.flatten()
    
    # Define the objective function for the optimizer
    def objective_func(positions):
        # Create a temporary DataFrame with the new node positions
        new_points_df = current_data["points"].copy()
        
        # We need to update the x and y coordinates for the specified nodes.
        for i, node_id in enumerate(nodes_to_optimize):
            new_points_df.loc[new_points_df['Node'] == node_id, ['x', 'y']] = positions[2*i:2*i+2]

        temp_data = current_data.copy()
        temp_data["points"] = new_points_df
        
        # Calculate the objective score with the new positions
        score, metrics, _ = get_objective(temp_data, weights)
        
        print(f"Current score: {score:.4f}, Metrics: {metrics}")
        return score

    # Define optimization constraints (optional)
    # bounds = [(0, 10)] * len(initial_positions) # Example bounds
    
    # Run the optimization
    result = minimize(objective_func, initial_positions, method='Nelder-Mead')
    
    # Recreate the final data with the optimized node positions
    final_positions = result.x
    
    final_points_df = current_data["points"].copy()
    for i, node_id in enumerate(nodes_to_optimize):
        final_points_df.loc[final_points_df['Node'] == node_id, ['x', 'y']] = final_positions[2*i:2*i+2]
    
    final_data = current_data.copy()
    final_data["points"] = final_points_df

    # Get the final metrics and return
    final_score, final_metrics, _ = get_objective(final_data, weights)
    
    return final_data, final_score, final_metrics

# Example usage (for testing)
if __name__ == "__main__":
    from truss_analysis import load_truss_data
    
    # Load from CSVs
    data = load_truss_data(
        "data/design_3/points.csv",
        "data/design_3/trusses.csv",
        "data/design_3/supports.csv",
        "data/design_3/materials.csv",
        loads_csv="data/design_3/loads.csv"
    )
    
    # Define which nodes to optimize (e.g., node 2)
    nodes_to_optimize = [2]
    
    # Define weights for the objectives
    weights = {
        'safety_margin': 1.0,
        'buckling_penalty': 1000.0,
        'material_cost': 1000.0,
        'average_force_magnitude': 0.1,
    }
    
    print("Starting optimization...")
    optimized_data, final_score, final_metrics = optimize_truss(data, nodes_to_optimize, weights)
    
    print("\n--- Optimization Complete ---")
    print(f"Final Score: {final_score:.4f}")
    print("Final Metrics:")
    for key, value in final_metrics.items():
        if isinstance(value, float):
            print(f"{key}: {value:.4f}")
        else:
            print(f"{key}: {value}")
    
    print("\nFinal Optimized Points:")
    print(optimized_data['points'])
