# truss_model.py

import os
import pandas as pd
import numpy as np
from . import fem_solver  # Use the new solver file
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
            self.loads = pd.read_csv(loads_path) if os.path.exists(loads_path) else None
            
            # Store initial state after loading
            self.initial_points = self.points.copy()
            self._calculate_initial_lengths()
            
            # Run an initial analysis to get baseline forces
            self.run_analysis()
            if not self.stresses_df.empty:
                self.initial_forces = self.stresses_df['axial_force'].copy()

            return True, "Data loaded successfully."
        except FileNotFoundError as e:
            return False, f"Error: File not found: {e.filename}"
        except Exception as e:
            return False, f"An unexpected error occurred: {e}"

    def _calculate_initial_lengths(self):
        """Calculate the original length of each truss member."""
        lengths = []
        node_coords = self.initial_points.set_index('Node')[['x', 'y']]
        for _, row in self.trusses.iterrows():
            p1 = node_coords.loc[row['start']].values
            p2 = node_coords.loc[row['end']].values
            lengths.append(np.linalg.norm(p2 - p1))
        self.initial_lengths = pd.Series(lengths, index=self.trusses.index)

    def run_analysis(self):
        """Runs the FEM simulation on the current truss geometry."""
        try:
            self.stresses_df, self.displacements = fem_solver.truss_analyze(
                self.points, self.trusses, self.supports, self.materials, self.loads
            )
        except Exception as e:
            print(f"Truss solver failed: {e}")
            self.stresses_df, self.displacements = pd.DataFrame(), np.array([])
        self.is_analyzed = True

    def update_node_positions(self, nodes_to_optimize, new_positions_flat):
        """Updates the x, y coordinates for a given set of nodes."""
        self.is_analyzed = False # Position changed, analysis is now stale
        for i, node_id in enumerate(nodes_to_optimize):
            self.points.loc[self.points['Node'] == node_id, ['x', 'y']] = new_positions_flat[2*i:2*i+2]
            
    def copy(self):
        """Creates a deep copy of the model instance."""
        return copy.deepcopy(self)