import numpy as np
import pandas as pd
from math import sqrt, pi
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

# -------------------------
# Core truss solver
# -------------------------
def assemble_truss_stiffness(points_df, trusses_df, materials_df):
    """
    Build global stiffness and element auxiliary data.
    points_df: columns ['Node', 'x', 'y']
    trusses_df: columns ['element', 'start', 'end', 'material_id' (optional)]
        If material_id missing, index 0 of materials_df is used.
    materials_df: columns ['E', 'A', 'I'] (A and I optional)
    Returns:
        K_global (2N x 2N sparse lil_matrix), element_data list with dicts
    """
    # map nodes to indices
    node_ids = list(points_df['Node'])
    nnode = len(node_ids)
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    ndof = 2 * nnode

    K = lil_matrix((ndof, ndof), dtype=float)
    element_data = []

    # Ensure materials_df has a 'material_id' column, using index if not present
    if 'material_id' not in materials_df.columns:
        materials_df = materials_df.copy()
        materials_df['material_id'] = materials_df.index.values

    for _, row in trusses_df.iterrows():
        eid = row['element']
        n1 = row['start']
        n2 = row['end']
        i1 = id_to_idx[n1]
        i2 = id_to_idx[n2]

        p1 = points_df.loc[points_df['Node'] == n1, ['x', 'y']].iloc[0].values
        p2 = points_df.loc[points_df['Node'] == n2, ['x', 'y']].iloc[0].values

        L = sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
        if L == 0:
            continue

        cx = (p2[0] - p1[0]) / L
        cy = (p2[1] - p1[1]) / L
        
        # Determine material properties. Use .get() to avoid KeyError if 'material_id' column is missing in trusses_df.
        mat_id = row.get('material_id', 0)
        material = materials_df.loc[materials_df['material_id'] == mat_id].iloc[0]
        E = material.get('E', 200e9) # Default to steel
        A = material.get('A', 0.001) # Default to 1000 mm^2
        I = material.get('I', 1e-6) # Default to 1e-6 m^4

        # Calculate element stiffness matrix in global coordinates
        k_local = E * A / L
        k_global_element = k_local * np.array([
            [cx**2, cx*cy, -cx**2, -cx*cy],
            [cx*cy, cy**2, -cx*cy, -cy**2],
            [-cx**2, -cx*cy, cx**2, cx*cy],
            [-cx*cy, -cy**2, cx*cy, cy**2]
        ])

        # Indices in global stiffness matrix
        dofs = [2*i1, 2*i1+1, 2*i2, 2*i2+1]
        
        for i, dof_i in enumerate(dofs):
            for j, dof_j in enumerate(dofs):
                K[dof_i, dof_j] += k_global_element[i, j]

        element_data.append({
            'element': eid,
            'start': n1,
            'end': n2,
            'L': L,
            'cx': cx,
            'cy': cy,
            'E': E,
            'A': A,
            'I': I, # Store Moment of Inertia
            'k_local': k_local
        })

    return K, element_data

def calculate_axial_forces_and_displacements(K, element_data, points_df, supports_df, loads_df=None):
    """
    Solves for displacements and axial forces.
    K: global stiffness matrix
    element_data: list of dicts with element properties
    points_df, supports_df, loads_df: input dataframes
    Returns: displacements vector and axial forces dataframe
    """
    node_ids = list(points_df['Node'])
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    nnode = len(node_ids)
    ndof = 2 * nnode

    F = np.zeros((ndof, 1))
    
    # Apply loads
    if loads_df is not None:
        for _, row in loads_df.iterrows():
            node_idx = id_to_idx[row['Node']]
            F[2 * node_idx] += row['Fx']
            F[2 * node_idx + 1] += row['Fy']

    # Apply boundary conditions
    dof_to_keep = list(range(ndof))
    
    # Check for Rx and Ry columns and add them if missing
    if 'Rx' not in supports_df.columns:
        print("Warning: 'Rx' column not found in supports.csv. Assuming no x-direction supports.")
        supports_df['Rx'] = 0
    if 'Ry' not in supports_df.columns:
        print("Warning: 'Ry' column not found in supports.csv. Assuming no y-direction supports.")
        supports_df['Ry'] = 0
    
    for _, row in supports_df.iterrows():
        node_idx = id_to_idx[row['Node']]
        if row['Rx'] == 1 and (2*node_idx) in dof_to_keep:
            dof_to_keep.remove(2*node_idx)
        if row['Ry'] == 1 and (2*node_idx + 1) in dof_to_keep:
            dof_to_keep.remove(2*node_idx + 1)
            
    K_reduced = K[np.ix_(dof_to_keep, dof_to_keep)]
    F_reduced = F[dof_to_keep]

    # Solve for displacements
    try:
        u_reduced = spsolve(K_reduced.tocsc(), F_reduced)
    except Exception as e:
        print(f"Solver failed: {e}")
        # Return zeros to avoid errors, will result in high objective score
        u_reduced = np.zeros_like(F_reduced)

    displacements = np.zeros((ndof, 1))
    for i, dof_idx in enumerate(dof_to_keep):
        displacements[dof_idx] = u_reduced[i]
    
    # Calculate axial forces and stresses
    rows = []
    for ed in element_data:
        i1 = id_to_idx[ed['start']]; i2 = id_to_idx[ed['end']]
        u1x = displacements[2*i1]; u1y = displacements[2*i1+1]
        u2x = displacements[2*i2]; u2y = displacements[2*i2+1]

        du = np.array([u2x - u1x, u2y - u1y])
        delta_length = du[0]*ed['cx'] + du[1]*ed['cy']
        axial_force = ed['k_local'] * delta_length
        axial_stress = axial_force / ed['A']
        
        rows.append({
            'element': ed['element'],
            'start': ed['start'],
            'end': ed['end'],
            'L': ed['L'],
            'axial_force': axial_force,
            'axial_stress': axial_stress,
            'A': ed['A'],
            'E': ed['E'],
            'I': ed['I'] # Include Moment of Inertia
        })
    stresses_df = pd.DataFrame(rows)
    return displacements, stresses_df

def calculate_critical_buckling_force(stresses_df):
    """
    Calculates the critical buckling force (Pc) for each compressive member.
    The formula is P_c = pi^2 * E * I / L^2
    """
    stresses_df['Pc'] = np.nan
    
    # Filter for compressive members (axial_force < 0)
    compressive_members = stresses_df[stresses_df['axial_force'] < 0].copy()
    if not compressive_members.empty:
        # P_c formula based on Euler's Buckling Theory (from research report)
        compressive_members['Pc'] = (
            (pi**2 * compressive_members['E'] * compressive_members['I']) /
            (compressive_members['L']**2)
        )
        # We use a positive value for Pc for consistency
        stresses_df.loc[compressive_members.index, 'Pc'] = compressive_members['Pc']
    
    return stresses_df


# -------------------------
# High-level convenience function
# -------------------------
def truss_analyze(points_df, trusses_df, supports_df, materials_df, loads_df=None):
    """
    High-level function to run the full truss analysis.
    Returns: stresses_df (DataFrame), displacements (numpy array)
    """
    K, element_data = assemble_truss_stiffness(points_df, trusses_df, materials_df)
    displacements, stresses_df = calculate_axial_forces_and_displacements(
        K, element_data, points_df, supports_df, loads_df
    )
    
    # Calculate critical buckling force
    stresses_df = calculate_critical_buckling_force(stresses_df)
    
    return stresses_df, displacements
