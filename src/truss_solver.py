import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from math import sqrt
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
    materials_df: columns ['E', 'A']  (A optional -> defaults to 1.0)
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

    for _, row in trusses_df.iterrows():
        eid = row['element']
        n1 = row['start']
        n2 = row['end']
        i1 = id_to_idx[n1]
        i2 = id_to_idx[n2]
        x1, y1 = float(points_df.loc[points_df['Node']==n1, 'x'].values[0]), float(points_df.loc[points_df['Node']==n1, 'y'].values[0])
        x2, y2 = float(points_df.loc[points_df['Node']==n2, 'x'].values[0]), float(points_df.loc[points_df['Node']==n2, 'y'].values[0])

        dx = x2 - x1
        dy = y2 - y1
        L = sqrt(dx*dx + dy*dy)
        if L <= 0:
            raise ValueError(f"Element {eid} has zero length between nodes {n1} and {n2}")

        cx = dx / L
        cy = dy / L

        # select material
        mid = row.get('material_id', None) if 'material_id' in row.index else None
        if mid is None:
            mat = materials_df.iloc[0]
        else:
            # allow either index or id lookup if materials have an 'id' column
            if 'id' in materials_df.columns:
                mat = materials_df.loc[materials_df['id'] == mid].iloc[0]
            else:
                # assume mid is integer index
                mat = materials_df.iloc[int(mid)]

        E = float(mat['E'])
        A = float(mat['A']) if 'A' in mat.index else 1.0
        k_local = (E * A) / L

        # element stiffness in global coords (4x4)
        # k = k_local * [ [ c^2  c*s -c^2 -c*s],
        #                 [ c*s s^2 -c*s -s^2],
        #                 [.. symmetric .. ] ]
        k = k_local * np.array([
            [ cx*cx, cx*cy, -cx*cx, -cx*cy],
            [ cx*cy, cy*cy, -cx*cy, -cy*cy],
            [-cx*cx,-cx*cy, cx*cx,  cx*cy],
            [-cx*cy,-cy*cy, cx*cy,  cy*cy],
        ])

        dof_map = [2*i1, 2*i1+1, 2*i2, 2*i2+1]

        # assemble
        for a in range(4):
            for b in range(4):
                K[dof_map[a], dof_map[b]] += k[a, b]

        element_data.append({
            'element': eid,
            'start': n1,
            'end': n2,
            'i1': i1,
            'i2': i2,
            'L': L,
            'cx': cx,
            'cy': cy,
            'E': E,
            'A': A,
            'k_local': k_local
        })

    return K, element_data, id_to_idx

def apply_supports_and_solve(K, points_df, supports_df, loads_df=None):
    """
    K: global stiffness (sparse)
    supports_df: columns ['Node', 'fix_x', 'fix_y'] (fix_* 1 or True to fix)
    loads_df: optional DataFrame ['Node','Fx','Fy'] otherwise zeros
    Returns: displacement vector u (2N,)
    """
    node_ids = list(points_df['Node'])
    nnode = len(node_ids)
    ndof = 2*nnode
    id_to_idx = {nid: i for i, nid in enumerate(node_ids)}
    F = np.zeros(ndof)

    # apply loads
    if loads_df is not None and not loads_df.empty:
        for _, r in loads_df.iterrows():
            nid = r['Node']
            if nid not in id_to_idx:
                continue
            idx = id_to_idx[nid]
            Fx = float(r.get('Fx', 0.0))
            Fy = float(r.get('Fy', 0.0))
            F[2*idx] = Fx
            F[2*idx+1] = Fy

    # supports -> build boolean mask of free DOFs
    fixed = np.zeros(ndof, dtype=bool)
    if supports_df is not None and not supports_df.empty:
        for _, r in supports_df.iterrows():
            nid = r['Node']
            if nid not in id_to_idx:
                continue
            idx = id_to_idx[nid]
            if int(r.get('fix_x', 0)):
                fixed[2*idx] = True
            if int(r.get('fix_y', 0)):
                fixed[2*idx+1] = True

    free_dofs = np.where(~fixed)[0]
    if free_dofs.size == 0:
        raise ValueError("No free DOFs: everything fixed!")

    # reduce K and F
    K_ff = K[free_dofs,:][:,free_dofs].tocsr()
    F_f = F[free_dofs]

    # solve
    u = np.zeros(ndof)
    u_f = spsolve(K_ff, F_f)
    u[free_dofs] = u_f
    return u

def compute_element_forces_and_stresses(element_data, displacements, points_df):
    """
    element_data: list produced by assemble_truss_stiffness
    displacements: global displacement vector u (2N)
    Returns: pandas.DataFrame with element, axial_force, axial_stress, length, etc.
    Sign convention: positive axial_force = tension
    """
    rows = []
    for ed in element_data:
        i1 = ed['i1']; i2 = ed['i2']
        u1x = displacements[2*i1]; u1y = displacements[2*i1+1]
        u2x = displacements[2*i2]; u2y = displacements[2*i2+1]

        # axial deformation projected along element
        du = np.array([u2x - u1x, u2y - u1y])
        delta_length = du[0]*ed['cx'] + du[1]*ed['cy']
        axial_force = ed['k_local'] * delta_length  # EA/L * delta_length
        axial_stress = axial_force / ed['A']
        rows.append({
            'element': ed['element'],
            'start': ed['start'],
            'end': ed['end'],
            'L': ed['L'],
            'axial_force': axial_force,
            'axial_stress': axial_stress,
            'A': ed['A'],
            'E': ed['E']
        })
    return pd.DataFrame(rows)

# -------------------------
# High-level convenience function
# -------------------------
def truss_analyze(points_df, trusses_df, supports_df, materials_df, loads_df=None):
    """
    Returns: stresses_df, displacements (numpy array)
    """
    K, element_data, id_to_idx = assemble_truss_stiffness(points_df, trusses_df, materials_df)
    u = apply_supports_and_solve(K, points_df, supports_df, loads_df)
    stresses_df = compute_element_forces_and_stresses(element_data, u, points_df)
    return stresses_df, u
