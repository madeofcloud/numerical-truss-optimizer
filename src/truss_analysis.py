import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from truss_solver import truss_analyze

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
def calculate_buckling_indices(stresses_df, alpha, lambd):
    """
    Calculates the weighted mean, weighted variance, and safety margin
    based on the equations in SSA 3.
    """
    df = stresses_df.copy()
    
    # Filter for compressive members
    compressive_df = df[df["axial_force"] < 0].copy()
    
    if compressive_df.empty:
        return {
            "gamma": np.nan,
            "s_mu_sq": np.nan,
            "s_mu": np.nan,
            "safety_margin": np.nan,
        }

    # Calculate utilization ratio mu_i
    # P_c,i = alpha / (lambda^2 * L_0,i^2)
    # mu_i = |T_i / P_c,i| = |axial_force / (alpha / (lambda^2 * L_0,i^2))|
    # L_0,i is the original member length of any element i
    compressive_df['mu'] = np.abs(compressive_df['axial_force']) * (lambd**2 * compressive_df['L']**2) / alpha
    
    # Calculate statistical weight omega_i.
    # We can simplify this for the calculation of gamma and s_mu^2 as shown in the derivation
    # in SSA 3, where only T_i remains.
    # The relevant term is the denominator in the final expressions for gamma and s_mu^2, which is sum(T_i).
    sum_T = compressive_df['axial_force'].abs().sum()
    
    if sum_T == 0:
        return {
            "gamma": np.nan,
            "s_mu_sq": np.nan,
            "s_mu": np.nan,
            "safety_margin": np.nan,
        }

    # Calculate weighted mean gamma
    # gamma = sum(T_i * mu_i) / sum(T_i)
    gamma = (compressive_df['axial_force'].abs() * compressive_df['mu']).sum() / sum_T
    
    # Calculate weighted variance s_mu^2
    # s_mu^2 = sum(T_i * (mu_i - gamma)^2) / sum(T_i)
    s_mu_sq = (compressive_df['axial_force'].abs() * (compressive_df['mu'] - gamma)**2).sum() / sum_T
    s_mu = np.sqrt(s_mu_sq)
    
    # Calculate safety margin
    safety_margin = gamma + 2 * s_mu

    return {
        "gamma": gamma,
        "s_mu_sq": s_mu_sq,
        "s_mu": s_mu,
        "safety_margin": safety_margin,
    }


def get_objective(stresses_df, displacements, points, trusses, alpha=5.16e3, lambd=1.0):
    """
    Objective function based on the safety margin: gamma + 2*s_mu.
    This value should be minimized.
    """
    indices = calculate_buckling_indices(stresses_df, alpha, lambd)
    return indices["safety_margin"]

# --------------------------
# 4) Iterate over node positions
# --------------------------
def vary_node_position(data, node_to_move, x_positions, y_positions, objective_fn=None, plot=True):
    """
    Move one node over a set of x and y positions and record results.
    Default objective: safety margin from buckling analysis.
    
    This function now includes geometric constraints on the node's position.
    """
    if objective_fn is None:
        objective_fn = get_objective

    base_points = data["points"].copy()
    results = []

    for x in x_positions:
        for y in y_positions:
            # Apply geometric constraints to the potential new position
            # Constraint 1: y-coordinate cannot be higher than 0.9
            # Constraint 2: Cannot enter the region past the rectangle with corners at (0.5,0) and (infty,0.5),
            # which means x must not be > 0.5 while y < 0.5.
            if y > 0.9 or (x > 0.5 and y < 0.55):
                results.append({"x": x, "y": y, "objective": np.nan})
                continue
            
            pts = base_points.copy()
            # Update the position of the specified node
            pts.loc[pts['Node'] == node_to_move, 'x'] = x
            pts.loc[pts['Node'] == node_to_move, 'y'] = y

            temp_data = data.copy()
            temp_data["points"] = pts  # update geometry

            try:
                stresses_df, u = run_truss_simulation(temp_data)
                obj = objective_fn(stresses_df, u, pts, data["trusses"])
            except Exception as e:
                # print(f"Error at x={x}, y={y}: {e}")
                obj = np.nan

            results.append({"x": x, "y": y, "objective": obj})

    results_df = pd.DataFrame(results)

    # --- plot ---
    if plot:
        plot_df = results_df.dropna(subset=["objective"]).drop_duplicates(subset=["x","y"])
        if len(plot_df) >= 3:
            fig = plt.figure(figsize=(8, 6))
            ax = fig.add_subplot(111, projection="3d")
            ax.plot_trisurf(plot_df["x"], plot_df["y"], plot_df["objective"],
                           cmap="viridis", edgecolor="none")
            ax.set_xlabel("x-position")
            ax.set_ylabel("y-position")
            ax.set_zlabel("Buckling Factor")
            ax.set_title(f"Buckling Factor vs Node {node_to_move} Position")
            plt.show()
        else:
            print("Not enough valid points for 3D surface plot.")

    return results_df


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
    indices = calculate_buckling_indices(stresses, alpha=5.16e3, lambd=1.0)
    print("\nInitial design buckling indices:")
    for key, value in indices.items():
        print(f"{key}: {value:.4f}")

    # Define a grid for node movement
    # Original node position
    x0, y0 = 0.5, 0.5
    delta = 0.1  # move ±0.1 in each direction
    n_points = 15  # 5x5 grid
    x_positions = np.linspace(x0 - delta, x0 + delta, n_points)
    y_positions = np.linspace(y0 - delta, y0 + delta, n_points)

    # Run sweep and plot using the safety margin objective
    print("\nRunning node variation sweep...")
    results_df = vary_node_position(
        data,
        node_to_move=6,
        x_positions=x_positions,
        y_positions=y_positions,
        objective_fn=get_objective
    )
    
    print("\nOptimization results DataFrame:")
    print(results_df)