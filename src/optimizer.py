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

        # Ensure original geometry is stored for normalization purposes
        if "original_points" not in temp_data:
            temp_data["original_points"] = data["points"].copy()
        if "original_trusses" not in temp_data:
            temp_data["original_trusses"] = data["trusses"].copy()
        if "original_lengths" not in temp_data:
            temp_data["original_lengths"] = data["L"].copy() if "L" in data else None
        # if "original_forces" not in temp_data:
        #     temp_data["original_forces"] = data["original_forces"].copy() if "original_forces" in data else None
        
        print(temp_data)  # Debug: print updated points

        # Calculate the objective score with the new positions
        score, metrics, _ = get_objective(temp_data, weights)
        
        # print(f"Current score: {score:.4f}, Metrics: {metrics}") # Verbose output removed for cleaner execution
        return score

    # Define optimization constraints (Based on the problem statement)
    def constraint_y(val):
        # val is a flattened array [x0, y0, x1, y1, ..., xn, yn]
        # return positive when constraints are satisfied
        return [0.9 - val[i + 1] for i in range(0, len(val), 2)]  # y <= 0.9 => 0.9 - y >= 0


    def constraint_region(val):
        # Returns positive if point is outside the forbidden zone (0.5 < x < 1.1 and y < 0.5)
        constraints = []
        for i in range(0, len(val), 2):
            x, y = val[i], val[i + 1]
            if 0.5 < x < 1.1:
                constraints.append(y - 0.5)  # y >= 0.5 in this region => y - 0.5 >= 0
            else:
                constraints.append(0.0)  # no constraint violation
        return constraints


    def constraint_x_upper(val):
        # x <= 1.2 => 1.2 - x >= 0
        return [1.2 - val[i] for i in range(0, len(val), 2)]


    # Combine constraints
    constraints = [
        {'type': 'ineq', 'fun': constraint_y},
        {'type': 'ineq', 'fun': constraint_region},
        {'type': 'ineq', 'fun': constraint_x_upper}
    ]

    # Optionally define bounds (e.g., x and y in [0, 2])
    bounds = [(0, 2)] * len(initial_positions)  # if desired
    
    # Run the optimization
    # Run optimizer with constraints
    result = minimize(
        objective_func,
        initial_positions,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'disp': True}
    )
    # result = minimize(objective_func, initial_positions, method='Nelder-Mead')
    
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
    # Example loading has been omitted for brevity
    pass