# fem_solver.py

import numpy as np
import pandas as pd
from math import sqrt, pi
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

def assemble_truss_stiffness(points_df, trusses_df, materials_df):
    """Build global stiffness and element auxiliary data for a 3D truss."""
    node_ids = list(points_df['Node'])
    nnode = len(node_ids)
    # The canonical mapping used for K and the global displacement vector
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    
    # CRITICAL FIX: 3 Degrees of Freedom (DOF) per node: u_x, u_y, u_z
    ndof = 3 * nnode 

    K = lil_matrix((ndof, ndof), dtype=float)
    element_data = []
    
    # Create a material lookup table indexed by row index (material_id)
    material_lookup = materials_df.set_index(materials_df.index)

    for _, row in trusses_df.iterrows():
        eid = row['element']
        n1 = row['start']
        n2 = row['end']
        i1 = id_to_idx[n1]
        i2 = id_to_idx[n2]

        # Retrieve x, y, and z coordinates for 3D analysis
        p1 = points_df.loc[points_df['Node'] == n1, ['x', 'y', 'z']].iloc[0].values
        p2 = points_df.loc[points_df['Node'] == n2, ['x', 'y', 'z']].iloc[0].values

        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        dz = p2[2] - p1[2]

        L = sqrt(dx**2 + dy**2 + dz**2)
        
        # Calculate direction cosines
        cx = dx / L
        cy = dy / L
        cz = dz / L
        
        # Robust Material Lookup by Index
        material_idx = row['material_id']
        if material_idx not in material_lookup.index:
            material = material_lookup.iloc[0]
        else:
            material = material_lookup.loc[material_idx] 
            
        E = material['E']
        A = material['A']
        I = material['I'] # Used for buckling check

        # Element stiffness in local coordinates (k_local)
        k_local = (A * E) / L

        # Direction cosine vector (3 components)
        c = np.array([cx, cy, cz])
        
        # Element stiffness matrix in global coordinates (6x6 matrix for 3D truss)
        C_matrix = np.outer(c, c) 
        K_e = np.zeros((6, 6))
        
        # Populate the 4 quadrants of the 6x6 element stiffness matrix
        K_e[0:3, 0:3] = k_local * C_matrix
        K_e[0:3, 3:6] = -k_local * C_matrix
        K_e[3:6, 0:3] = -k_local * C_matrix
        K_e[3:6, 3:6] = k_local * C_matrix

        # Global DOF indices for this element (i1: start node, i2: end node)
        # Note: 3*i maps to ux, 3*i+1 maps to uy, 3*i+2 maps to uz
        dof = [3*i1, 3*i1+1, 3*i1+2, 3*i2, 3*i2+1, 3*i2+2]

        # Add element stiffness to global matrix K
        for r_local, r_global in enumerate(dof):
            for c_local, c_global in enumerate(dof):
                K[r_global, c_global] += K_e[r_local, c_local] 

        # Store auxiliary data
        element_data.append({
            'element': eid, 'start': n1, 'end': n2, 'L': L, 
            'cx': cx, 'cy': cy, 'cz': cz, 'E': E, 'A': A, 'I': I, 
            'k_local': k_local, 'dof': dof
        })

    return K, element_data, ndof

def solve_system(K, supports_df, loads_df, points_df, ndof):
    """Applies boundary conditions and solves for displacements."""
    
    # Ensure node indexing is canonical (from points_df)
    node_ids = list(points_df['Node'])
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    
    # 1. Initialize Force vector F
    F = np.zeros(ndof)
    
    # Apply loads
    if loads_df is not None and not loads_df.empty:
        for _, row in loads_df.iterrows():
            node_idx = id_to_idx.get(row['Node'])
            if node_idx is not None:
                # Fx: 3*idx, Fy: 3*idx+1, Fz: 3*idx+2
                F[3 * node_idx] += row.get('Fx', 0.0)
                F[3 * node_idx + 1] += row.get('Fy', 0.0)
                F[3 * node_idx + 2] += row.get('Fz', 0.0)

    # 2. Identify constrained DOF
    constrained_dof = []
    
    for _, row in supports_df.iterrows():
        node_idx = id_to_idx.get(row['Node'])
        if node_idx is not None:
            # Check for supports in x, y, and z directions (3 DOF per node)
            if row.get('Rx', 0) == 1: # NOTE: Using Rx, Ry, Rz from supports.csv
                constrained_dof.append(3 * node_idx)
            if row.get('Ry', 0) == 1:
                constrained_dof.append(3 * node_idx + 1)
            if row.get('Rz', 0) == 1:
                constrained_dof.append(3 * node_idx + 2)

    all_dof = set(range(ndof))
    free_dof = sorted(list(all_dof - set(constrained_dof)))
    
    # Check for rigid body motion (minimum 6 constraints needed)
    if ndof > 0 and len(constrained_dof) < 6:
        pass # The singular matrix check below is more robust

    if not free_dof:
        # Structure is fully fixed, no displacements possible
        return np.zeros(ndof), free_dof

    # 3. Reduce K and F
    K_red = K.tocsr()[free_dof, :].tocsc()[:, free_dof]
    F_red = F[free_dof]

    # Check for mechanism/singularity after reduction
    if K_red.shape[0] != K_red.shape[1] or K_red.shape[0] == 0:
         raise ValueError("Reduced stiffness matrix has invalid dimensions.")
    
    # Robust singularity check
    try:
        cond_num = np.linalg.cond(K_red.todense())
        if cond_num > 1e12:
             raise ValueError(f"Global stiffness matrix is singular or ill-conditioned. Condition Number: {cond_num:.2e}. Structure is likely a mechanism or improperly supported.")
    except:
         # Handle case where dense conversion fails or numpy errors out on singular matrix
         raise ValueError("Global stiffness matrix is singular or ill-conditioned. Structure is likely a mechanism or improperly supported.")


    # 4. Solve K_red * U_red = F_red
    U_red = spsolve(K_red, F_red)

    # 5. Expand solution to full displacement vector
    displacements = np.zeros(ndof)
    for i, dof in enumerate(free_dof):
        displacements[dof] = U_red[i]
        
    return displacements, free_dof

def calculate_element_forces(displacements, element_data, points_df):
    """Calculates internal forces and stresses for 3D truss elements."""
    rows = []
    
    # Ensure node indexing is canonical (from points_df)
    node_ids = list(points_df['Node'])
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    
    for ed in element_data:
        n1 = ed['start']
        n2 = ed['end']
        
        # Use the canonical map
        i1 = id_to_idx[n1] 
        i2 = id_to_idx[n2]

        # Element displacement vector (3 DOF per node)
        # FIX: Ensure all 3 DOFs are correctly extracted
        u1x = displacements[3*i1]
        u1y = displacements[3*i1+1]
        u1z = displacements[3*i1+2]
        u2x = displacements[3*i2]
        u2y = displacements[3*i2+1]
        u2z = displacements[3*i2+2]

        # Change in length (dot product of displacement vector with direction cosines)
        delta_length = (u2x - u1x) * ed['cx'] + (u2y - u1y) * ed['cy'] + (u2z - u1z) * ed['cz']
        
        # Axial force F = k_local * delta_length
        axial_force = ed['k_local'] * delta_length
        
        rows.append({
            'element': ed['element'], 'start': n1, 'end': n2,
            'L': ed['L'], 'axial_force': axial_force, 'axial_stress': axial_force / ed['A'],
            'A': ed['A'], 'E': ed['E'], 'I': ed['I']
        })
        
    stresses_df = pd.DataFrame(rows)
    return stresses_df

def calculate_critical_buckling_force(stresses_df):
    """Calculates the critical buckling force (Pc) for each compressive member."""
    stresses_df['Pc'] = np.nan
    compressive_mask = stresses_df['axial_force'] < 0
    if compressive_mask.any():
        compressive_members = stresses_df[compressive_mask]
        # Pc = (pi^2 * E * I) / L^2
        pc_values = (pi**2 * compressive_members['E'] * compressive_members['I']) / (compressive_members['L']**2)
        stresses_df.loc[compressive_mask, 'Pc'] = pc_values
    return stresses_df

def truss_analyze(points_df, trusses_df, supports_df, materials_df, loads_df=None):
    """Main function to perform 3D static truss analysis."""
    if 'z' not in points_df.columns:
        # Check to ensure 3D is possible
        raise ValueError("3D Analysis requires 'z' column in points.csv.")

    try:
        K, element_data, ndof = assemble_truss_stiffness(points_df, trusses_df, materials_df)
        
        # Pass points_df to solve_system for consistent node indexing
        displacements, _ = solve_system(K, supports_df, loads_df, points_df, ndof) 
        
        # Pass points_df to calculate_element_forces for consistent node indexing
        stresses_df = calculate_element_forces(displacements, element_data, points_df)
        stresses_df = calculate_critical_buckling_force(stresses_df)
        
        return stresses_df, displacements
        
    except ValueError as e:
        print(f"3D Truss solver failed: {e}")
        return pd.DataFrame(), np.array([])
    except Exception as e:
        print(f"An unexpected error occurred in the 3D Truss solver: {e}")
        return pd.DataFrame(), np.array([])
