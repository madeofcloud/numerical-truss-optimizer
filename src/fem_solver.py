# fem_solver.py

import numpy as np
import pandas as pd
from math import sqrt, pi
from scipy.sparse import lil_matrix
from scipy.sparse.linalg import spsolve

def assemble_truss_stiffness(points_df, trusses_df, materials_df):
    """Build global stiffness and element auxiliary data."""
    node_ids = list(points_df['Node'])
    nnode = len(node_ids)
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    ndof = 2 * nnode

    K = lil_matrix((ndof, ndof), dtype=float)
    element_data = []

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
        
        mat_id = row.get('material_id', 0)
        material = materials_df.loc[materials_df['material_id'] == mat_id].iloc[0]
        E = material.get('E', 200e9) 
        A = material.get('A', 0.001) 
        I = material.get('I', 1e-6)

        k_local = E * A / L
        k_global_element = k_local * np.array([
            [cx**2, cx*cy, -cx**2, -cx*cy],
            [cx*cy, cy**2, -cx*cy, -cy**2],
            [-cx**2, -cx*cy, cx**2, cx*cy],
            [-cx*cy, -cy**2, cx*cy, cy**2]
        ])

        dofs = [2*i1, 2*i1+1, 2*i2, 2*i2+1]
        
        for i, dof_i in enumerate(dofs):
            for j, dof_j in enumerate(dofs):
                K[dof_i, dof_j] += k_global_element[i, j]

        element_data.append({
            'element': eid, 'start': n1, 'end': n2, 'L': L, 'cx': cx, 'cy': cy,
            'E': E, 'A': A, 'I': I, 'k_local': k_local
        })

    return K, element_data

def calculate_axial_forces_and_displacements(K, element_data, points_df, supports_df, loads_df=None):
    """Solves for displacements and axial forces."""
    node_ids = list(points_df['Node'])
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    nnode = len(node_ids)
    ndof = 2 * nnode

    F = np.zeros((ndof, 1))
    
    if loads_df is not None:
        for _, row in loads_df.iterrows():
            node_idx = id_to_idx[row['Node']]
            F[2 * node_idx] += row['Fx']
            F[2 * node_idx + 1] += row['Fy']

    dof_to_keep = list(range(ndof))
    
    if 'Rx' not in supports_df.columns:
        supports_df['Rx'] = 0
    if 'Ry' not in supports_df.columns:
        supports_df['Ry'] = 0
    
    for _, row in supports_df.iterrows():
        node_idx = id_to_idx[row['Node']]
        if row['Rx'] == 1 and (2*node_idx) in dof_to_keep:
            dof_to_keep.remove(2*node_idx)
        if row['Ry'] == 1 and (2*node_idx + 1) in dof_to_keep:
            dof_to_keep.remove(2*node_idx + 1)
            
    K_reduced = K[np.ix_(dof_to_keep, dof_to_keep)]
    F_reduced = F[dof_to_keep]

    try:
        u_reduced = spsolve(K_reduced.tocsc(), F_reduced)
    except Exception:
        u_reduced = np.zeros_like(F_reduced)

    displacements = np.zeros((ndof, 1))
    displacements[dof_to_keep] = u_reduced.reshape(-1, 1)
    
    rows = []
    for ed in element_data:
        i1 = id_to_idx[ed['start']]; i2 = id_to_idx[ed['end']]
        u1x, u1y = displacements[2*i1], displacements[2*i1+1]
        u2x, u2y = displacements[2*i2], displacements[2*i2+1]

        delta_length = (u2x - u1x) * ed['cx'] + (u2y - u1y) * ed['cy']
        axial_force = ed['k_local'] * delta_length.item()
        
        rows.append({
            'element': ed['element'], 'start': ed['start'], 'end': ed['end'],
            'L': ed['L'], 'axial_force': axial_force, 'axial_stress': axial_force / ed['A'],
            'A': ed['A'], 'E': ed['E'], 'I': ed['I']
        })
    stresses_df = pd.DataFrame(rows)
    return displacements, stresses_df

def calculate_critical_buckling_force(stresses_df):
    """Calculates the critical buckling force (Pc) for each compressive member."""
    stresses_df['Pc'] = np.nan
    compressive_mask = stresses_df['axial_force'] < 0
    if compressive_mask.any():
        compressive_members = stresses_df[compressive_mask]
        pc_values = (pi**2 * compressive_members['E'] * compressive_members['I']) / (compressive_members['L']**2)
        stresses_df.loc[compressive_mask, 'Pc'] = pc_values
    return stresses_df

def truss_analyze(points_df, trusses_df, supports_df, materials_df, loads_df=None):
    """High-level function to run the full truss analysis."""
    K, element_data = assemble_truss_stiffness(points_df, trusses_df, materials_df)
    displacements, stresses_df = calculate_axial_forces_and_displacements(
        K, element_data, points_df, supports_df, loads_df
    )
    stresses_df = calculate_critical_buckling_force(stresses_df)
    return stresses_df, displacements