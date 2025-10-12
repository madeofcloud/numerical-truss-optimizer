# truss_model.py

import os
import pandas as pd
import numpy as np
from . import fem_solver
import copy

class TrussModel:
    """Encapsulates all data and operations for a truss design."""

    def __init__(self):
        # Input DataFrames
        self.points = pd.DataFrame()
        self.trusses = pd.DataFrame()
        self.supports = pd.DataFrame()
        self.materials = pd.DataFrame()
        self.loads = pd.DataFrame()
        
        # Store original state for normalization
        self.initial_points = pd.DataFrame()
        self.initial_lengths = pd.Series(dtype=float)
        self.initial_forces = pd.Series(dtype=float)

        # Analysis Results
        self.stresses_df = pd.DataFrame()
        self.displacements = np.array([])
        self.is_analyzed = False

    def load_from_directory(self, directory_path):
        """Loads all necessary CSV files from a given directory."""
        try:
            points_path = os.path.join(directory_path, "points.csv")
            trusses_path = os.path.join(directory_path, "trusses.csv")
            supports_path = os.path.join(directory_path, "supports.csv")
            materials_path = os.path.join(directory_path, "materials.csv")
            loads_path = os.path.join(directory_path, "loads.csv")
            
            self.points = pd.read_csv(points_path)
            self.trusses = pd.read_csv(trusses_path)
            self.supports = pd.read_csv(supports_path)
            self.materials = pd.read_csv(materials_path)
            
            # Check for optional loads file
            if os.path.exists(loads_path):
                self.loads = pd.read_csv(loads_path)
            else:
                self.loads = pd.DataFrame()

            # --- START Synchronization and Validation ---
            
            # 1. Handle missing 'material_id'
            if 'material_id' not in self.trusses.columns:
                print("Warning: 'material_id' column missing in trusses.csv. Assuming all elements use material index 0.")
                first_material_idx = self.materials.index[0] if not self.materials.empty else 0
                self.trusses['material_id'] = first_material_idx
                
            # 2. Ensure Z column exists for 3D compatibility
            if 'z' not in self.points.columns:
                self.points['z'] = 0.0
            
            # 3. Clean up and validate types
            self.points['Node'] = pd.to_numeric(self.points['Node'], downcast='integer', errors='coerce').fillna(-1).astype(int)
            self.supports['Node'] = pd.to_numeric(self.supports['Node'], downcast='integer', errors='coerce').fillna(-1).astype(int)
            
            self.trusses['element'] = pd.to_numeric(self.trusses['element'], downcast='integer', errors='coerce').fillna(-1).astype(int)
            self.trusses['start'] = pd.to_numeric(self.trusses['start'], downcast='integer', errors='coerce').fillna(-1).astype(int)
            self.trusses['end'] = pd.to_numeric(self.trusses['end'], downcast='integer', errors='coerce').fillna(-1).astype(int)
            self.trusses['material_id'] = pd.to_numeric(self.trusses['material_id'], downcast='integer', errors='coerce').fillna(-1).astype(int)
            
            # --- END Synchronization and Validation ---
            
            # Store initial state (deep copy required)
            self.initial_points = self.points.copy()
            
            self._calculate_initial_lengths()
            
        except Exception as e:
            # Re-raise non-pandas loading exceptions
            if "material_id" not in str(e):
                raise
            
    def copy(self):
        """Creates a deep copy of the TrussModel for use in optimization iterations."""
        return copy.deepcopy(self)

    def _calculate_initial_lengths(self):
        """Calculate the original length of each truss member. Uses 3D coordinates."""
        lengths = []
        # CRITICAL FIX: Ensure 'z' is included for 3D length calculation
        node_coords = self.initial_points.set_index('Node')[['x', 'y', 'z']] 
        for _, row in self.trusses.iterrows():
            p1 = node_coords.loc[row['start']].values
            p2 = node_coords.loc[row['end']].values
            # 3D distance calculation
            lengths.append(np.linalg.norm(p2 - p1)) 
        self.initial_lengths = pd.Series(lengths, index=self.trusses.index)

    def run_analysis(self):
        """Runs the FEM simulation on the current truss geometry."""
        try:
            # fem_solver.truss_analyze now handles 3D and consistent indexing
            self.stresses_df, self.displacements = fem_solver.truss_analyze(
                self.points, self.trusses, self.supports, self.materials, self.loads
            )
        except Exception as e:
            print(f"Truss solver failed: {e}")
            self.stresses_df, self.displacements = pd.DataFrame(), np.array([])
        self.is_analyzed = True

    def update_node_positions(self, nodes_to_optimize, new_positions_flat):
        """
        Updates the x, y, z coordinates for a given set of nodes. 
        Assumes new_positions_flat is a 1D array of [x1, y1, z1, x2, y2, z2, ...].
        """
        self.is_analyzed = False # Position changed, analysis is now stale
        for i, node_id in enumerate(nodes_to_optimize):
            # Index positions for x, y, z in the flat array (3 DOF)
            x_idx = 3 * i
            y_idx = 3 * i + 1
            z_idx = 3 * i + 2 # CRITICAL FIX: Ensure z is updated
            
            df_index = self.points[self.points['Node'] == node_id].index
            if not df_index.empty:
                idx = df_index[0]
                
                # Update x, y, z
                self.points.loc[idx, 'x'] = new_positions_flat[x_idx]
                self.points.loc[idx, 'y'] = new_positions_flat[y_idx]
                self.points.loc[idx, 'z'] = new_positions_flat[z_idx]
                
            else:
                print(f"Warning: Node ID {node_id} not found in points DataFrame during position update.")
