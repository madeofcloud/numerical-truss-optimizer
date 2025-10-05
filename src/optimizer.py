# optimizer.py

import numpy as np
from scipy.optimize import minimize
from analysis import get_objective

def optimize_truss(initial_model, nodes_to_optimize, weights, bounds=None, constraints=None):
    """
    Optimizes node positions of a truss model to minimize the objective score.
    
    Args:
        initial_model (TrussModel): The initial, configured truss model.
        nodes_to_optimize (list): List of node IDs to move.
        weights (dict): A dictionary of weights for the objectives.
        bounds (list, optional): Bounds for the optimizer variables.
        constraints (list, optional): Constraints for the optimizer.

    Returns:
        A tuple of (optimized_model, final_score, final_metrics).
    """
    initial_positions = initial_model.points.set_index('Node').loc[nodes_to_optimize, ['x', 'y']].values.flatten()

    # Objective function for the optimizer to minimize
    def objective_func(positions):
        # Work on a copy to avoid modifying the model across iterations
        temp_model = initial_model.copy()
        temp_model.update_node_positions(nodes_to_optimize, positions)
        
        # The get_objective function will run the analysis internally
        score, _ = get_objective(temp_model, weights)
        return score

    # Default bounds if not provided
    if bounds is None:
        bounds = [(None, None)] * len(initial_positions)

    # Default constraints if not provided
    if constraints is None:
        constraints = []

    # Run the optimization using SciPy's minimizer
    result = minimize(
        objective_func,
        initial_positions,
        method='SLSQP',
        bounds=bounds,
        constraints=constraints,
        options={'disp': True, 'maxiter': 100}
    )
    
    # Create the final, optimized model
    final_model = initial_model.copy()
    final_model.update_node_positions(nodes_to_optimize, result.x)
    
    # Get final score and metrics for reporting
    final_score, final_metrics = get_objective(final_model, weights)
    
    return final_model, final_score, final_metrics