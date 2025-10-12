# main_app.py

import sys
import os
import csv
from datetime import datetime
import pandas as pd
import numpy as np

# Convert ALL PyQt5 imports to PySide6
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTableWidget, QTableWidgetItem, QAbstractItemView,
                             QMessageBox, QSlider, QTabWidget, QGridLayout, QFrame,
                             QFileDialog, QSplitter, QCheckBox, QSizePolicy) 
from PySide6.QtCore import Qt, QByteArray 

# Refactored project imports
from .ui_themes import LIGHT_THEME, DARK_THEME
from .ui_components import Mpl3DCanvas # Now imports the 3D canvas with zoom
from .truss_model import TrussModel
from .optimizer import optimize_truss
from .analysis import get_objective

class OptimizerApp(QMainWindow):
    """Main application window for the 3D truss optimizer."""
    def __init__(self):
        super().__init__()
        
        self.model = None
        self.current_theme = "dark" 
        self.legend_labels = {} 
        
        self.setWindowTitle("3D Truss Optimizer & Analysis")
        self.setGeometry(100, 100, 1400, 900)

        self.output_dir = os.path.join(os.getcwd(), "truss_output")
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Dictionary to hold QLineEdits for easy access to weight values
        self.weight_inputs = {}

        self._init_ui()
        self.apply_theme(self.current_theme)

    # --- UI Initialization and Layout ---
    def _init_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        # Splitter to divide Plot/Controls (Left) and Tables (Right)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Panel (Plot, Controls, and Weights)
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # 3D Plotting Canvas
        self.canvas = Mpl3DCanvas(self, width=5, height=4, dpi=100)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_layout.addWidget(self.canvas)
        
        # Control Buttons (Load, Run, Status)
        control_frame = QFrame()
        control_layout = QGridLayout(control_frame)
        
        self.load_button = QPushButton("Load 3D Truss Data")
        self.load_button.clicked.connect(self._load_data)
        control_layout.addWidget(self.load_button, 0, 0)
        
        self.run_button = QPushButton("Run 3D Optimization")
        self.run_button.clicked.connect(self._run_optimization)
        self.run_button.setEnabled(False)
        control_layout.addWidget(self.run_button, 0, 1)

        self.status_label = QLabel("Ready to load 3D data.")
        control_layout.addWidget(self.status_label, 1, 0, 1, 2)
        
        left_layout.addWidget(control_frame)
        
        # Weight Controls UI
        self.weights_sliders = {}
        weight_controls = self._create_weight_controls()
        left_layout.addWidget(weight_controls)
        
        main_splitter.addWidget(left_widget)
        
        # Right Panel (Tables) - Tabs for Input, Metrics, Stresses
        self.tab_widget = QTabWidget()
        
        self.input_tab = self._create_input_tab()
        self.metrics_tab = self._create_metrics_tab()
        self.stresses_tab = self._create_stresses_tab()
        
        self.tab_widget.addTab(self.input_tab, "Model Data (3D)")
        self.tab_widget.addTab(self.metrics_tab, "Objective Metrics")
        self.tab_widget.addTab(self.stresses_tab, "Element Stresses")
        
        main_splitter.addWidget(self.tab_widget)
        
        main_widget.setLayout(QHBoxLayout())
        main_widget.layout().addWidget(main_splitter)
        
        # Set initial split size (e.g., 60% for plot, 40% for tables)
        main_splitter.setSizes([800, 600])

    def _create_weight_controls(self):
        """Creates the frame and widgets for setting optimization objective weights."""
        # frame = QFrame()
        # frame.setWindowTitle("Objective Weights")
        # layout = QGridLayout(frame)
        
        # # Get default weights to populate the initial UI
        # weights_data = self._get_default_weights(as_init=True)
        
        # # Labels and inputs for each weight
        # row = 0
        # for key, value in weights_data.items():
        #     label = QLabel(key.replace('_', ' ').title() + ":")
        #     line_edit = QLineEdit(f"{value}")
        #     line_edit.setToolTip(f"Weight for {key.replace('_', ' ')}")
        #     line_edit.setFixedWidth(60)
            
        #     # Store the QLineEdit reference
        #     self.weight_inputs[key] = line_edit
            
        #     layout.addWidget(label, row, 0)
        #     layout.addWidget(line_edit, row, 1)
        #     row += 1
            
        # layout.setColumnStretch(0, 1) 
        # layout.setColumnStretch(1, 0) 
        # layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        param_group = QFrame()
        param_layout = QGridLayout(param_group)
        param_layout.addWidget(QLabel("<b>Optimization Weights</b>"), 0, 0, 1, 3)
        sliders_config = [
            ("Buckling Distribution Factor", 25.0), ("Buckling Penalty", 100.0),
            ("Material Usage", 50.0), ("Compression Uniformity", 10.0),
            ("Average Force Magnitude", 40.0),
        ]
        for row, (name, val) in enumerate(sliders_config, 1):
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 10000); slider.setValue(int(val*100))
            value_label = QLabel(f"{val:.2f}"); value_label.setFixedWidth(50)
            slider.valueChanged.connect(lambda v, lbl=value_label: lbl.setText(f"{v/100:.2f}"))
            param_layout.addWidget(QLabel(name), row, 0)
            param_layout.addWidget(slider, row, 1)
            param_layout.addWidget(value_label, row, 2)
            self.weights_sliders[name] = slider
        # layout.addWidget(param_group)
        return param_group

    def _create_input_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Points Table (now includes Z)
        layout.addWidget(QLabel("Node Coordinates (x, y, z)"))
        self.points_table = QTableWidget()
        self.points_table.setColumnCount(4)
        self.points_table.setHorizontalHeaderLabels(['Node', 'x', 'y', 'z'])
        self.points_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.points_table)
        
        return widget

    def _create_metrics_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("Optimization Performance Metrics"))
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(2)
        self.metrics_table.setHorizontalHeaderLabels(['Metric', 'Value'])
        self.metrics_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.metrics_table)
        
        return widget
        
    def _create_stresses_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        layout.addWidget(QLabel("Element Stress and Force Results (3D)"))
        self.stresses_table = QTableWidget()
        self.stresses_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.stresses_table)
        
        return widget
        
    # --- Data and UI Update Methods ---
    def apply_theme(self, theme_name):
        theme = DARK_THEME if theme_name == "dark" else LIGHT_THEME
        self.setStyleSheet(theme)
        
    def _update_points_table(self, df):
        """Populates the points table with 3D coordinates."""
        self.points_table.setRowCount(len(df))
        self.points_table.setColumnCount(4)
        self.points_table.setHorizontalHeaderLabels(['Node', 'x', 'y', 'z'])
        self.points_table.setSelectionMode(QAbstractItemView.MultiSelection)
        self.points_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        for i, row in df.iterrows():
            self.points_table.setItem(i, 0, QTableWidgetItem(str(row['Node'])))
            self.points_table.setItem(i, 1, QTableWidgetItem(f"{row['x']:.2f}"))
            self.points_table.setItem(i, 2, QTableWidgetItem(f"{row['y']:.2f}"))
            self.points_table.setItem(i, 3, QTableWidgetItem(f"{row['z']:.2f}"))

    def _update_metrics_table(self, metrics):
        """Populates the metrics table."""
        self.metrics_table.setRowCount(len(metrics))
        
        for i, (key, value) in enumerate(metrics.items()):
            self.metrics_table.setItem(i, 0, QTableWidgetItem(key))
            # Handle possible non-numeric values for error messages
            value_str = f"{value:.4f}" if isinstance(value, (int, float)) else str(value)
            self.metrics_table.setItem(i, 1, QTableWidgetItem(value_str))

    def _update_stresses_table(self, df):
        """Populates the stresses table."""
        
        # Check if the dataframe is empty (e.g., if analysis failed)
        if df.empty:
            self.stresses_table.setRowCount(1)
            self.stresses_table.setColumnCount(1)
            self.stresses_table.setHorizontalHeaderLabels(['Status'])
            self.stresses_table.setItem(0, 0, QTableWidgetItem("3D Analysis failed or no data available."))
            return
            
        # Ensure all required columns are present before proceeding
        required_cols = ['element', 'L', 'axial_force', 'axial_stress', 'Pc']
        if not all(col in df.columns for col in required_cols):
            self.stresses_table.setRowCount(1)
            self.stresses_table.setColumnCount(1)
            self.stresses_table.setHorizontalHeaderLabels(['Error'])
            self.stresses_table.setItem(0, 0, QTableWidgetItem("Analysis results are missing required columns."))
            return

        self.stresses_table.setRowCount(len(df))
        
        # Select columns to display
        display_cols = required_cols
        self.stresses_table.setColumnCount(len(display_cols))
        self.stresses_table.setHorizontalHeaderLabels(display_cols)
        
        for i, row in df.iterrows():
            for j, col in enumerate(display_cols):
                value = row[col]
                # Format specific columns
                if col in ['L', 'axial_force', 'axial_stress', 'Pc']:
                    item = QTableWidgetItem(f"{value:.2f}" if pd.notna(value) else 'N/A')
                else:
                    item = QTableWidgetItem(str(value))
                self.stresses_table.setItem(i, j, item)
                
    def _draw_truss(self, scale_factor=200):
        """Draws the 3D truss structure, forces, and displacements."""
        self.canvas.axes.cla() # Clear the previous plot

        points_df = self.model.points
        trusses_df = self.model.trusses
        stresses_df = self.model.stresses_df
        
        if points_df.empty:
            self.canvas.axes.set_title("3D Truss Plot (No data loaded)")
            self.canvas.draw()
            return
            
        # Check if stress data is valid for coloring (Fixes KeyError: 'element')
        is_stress_data_valid = 'element' in stresses_df.columns and not stresses_df.empty
            
        # Get current coordinates
        coords = points_df.set_index('Node')[['x', 'y', 'z']]
        X, Y, Z = coords['x'].values, coords['y'].values, coords['z'].values
        
        # --- 1. Draw Members (Trusses) ---
        for _, row in trusses_df.iterrows():
            p1 = coords.loc[row['start']].values
            p2 = coords.loc[row['end']].values
            
            # Line data for the 3D plot
            x_vals = [p1[0], p2[0]]
            y_vals = [p1[1], p2[1]]
            z_vals = [p1[2], p2[2]]
            
            # Determine color based on stress
            color = 'gray'
            if is_stress_data_valid:
                # This line is now safe because we checked if the 'element' column exists
                stress_row = stresses_df[stresses_df['element'] == row['element']]
                if not stress_row.empty:
                    stress = stress_row.iloc[0]['axial_stress']
                    if pd.notna(stress):
                        # Blue for compression (negative), Red for tension (positive)
                        if stress < 0:
                            color = '#007BFF' # Bright Blue for Compression
                        elif stress > 0:
                            color = '#DC3545' # Bright Red for Tension
                        
            self.canvas.axes.plot(x_vals, y_vals, z_vals, color=color, linewidth=2, marker='')

        # --- 2. Draw Nodes (Points) ---
        self.canvas.axes.scatter(X, Y, Z, c='k', marker='o', s=50, label='Nodes')
        
        # Annotate nodes
        for i, row in points_df.iterrows():
            self.canvas.axes.text(row['x'], row['y'], row['z'], str(row['Node']), color='black', fontsize=9, zdir='x')

        # --- 3. Draw Displaced Shape (if analyzed) ---
        # Only proceed if analysis was successful AND displacements are non-zero
        max_disp = np.max(np.abs(self.model.displacements)) if self.model.displacements.size > 0 else 0
        if self.model.is_analyzed and max_disp > 1e-9:
            U = self.model.displacements
            
            # Dynamic scale factor calculation for visualization purposes
            max_coord = np.max(np.abs(coords.values))
            
            # Calculate a scale factor to make max displacement visually noticeable (e.g., 5% of max structure size)
            u_scale = (0.05 * max_coord) / max_disp if max_disp > 1e-9 else 1.0 
            u_scale = max(1.0, u_scale) # Ensure factor is at least 1

            # Calculate displaced coordinates
            # Correcting the index slicing for X, Y, Z coordinates and U vector 
            # (Assuming U contains [u1x, u1y, u1z, u2x, u2y, u2z, ...] for nodes in the same order as points_df)
            X_displaced = X + U[::3] * u_scale
            Y_displaced = Y + U[1::3] * u_scale
            Z_displaced = Z + U[2::3] * u_scale

            # Draw displaced members
            for i, row in trusses_df.iterrows():
                i1_idx = points_df[points_df['Node'] == row['start']].index[0]
                i2_idx = points_df[points_df['Node'] == row['end']].index[0]

                p1_disp = np.array([X_displaced[i1_idx], Y_displaced[i1_idx], Z_displaced[i1_idx]])
                p2_disp = np.array([X_displaced[i2_idx], Y_displaced[i2_idx], Z_displaced[i2_idx]])

                self.canvas.axes.plot(
                    [p1_disp[0], p2_disp[0]], 
                    [p1_disp[1], p2_disp[1]], 
                    [p1_disp[2], p2_disp[2]], 
                    '--', color='#FFC107', linewidth=1, marker=''
                )

            # Draw displaced nodes
            self.canvas.axes.scatter(X_displaced, Y_displaced, Z_displaced, c='#FFC107', marker='o', s=30, label=f'Displaced (x{u_scale:.1f})')
            self.status_label.setText(self.status_label.text() + f" | Max Disp: {max_disp:.4e} (Scale: x{u_scale:.1f})")


        # --- 4. Set labels and aspect ratio (Plotting Fix) ---
        self.canvas.axes.set_xlabel('X Axis')
        self.canvas.axes.set_ylabel('Y Axis')
        self.canvas.axes.set_zlabel('Z Axis')
        self.canvas.axes.set_title("3D Truss Structure and Displacements (Scroll to Zoom)")
        
        # FIX: Ensure proper 3D aspect ratio and limits for visibility
        if X.size > 0:
            # Determine the maximum extent across all 3 axes
            max_range = np.array([X.max()-X.min(), Y.max()-Y.min(), Z.max()-Z.min()]).max() / 2.0
            max_range = max(1.0, max_range) # Ensure non-zero range

            mid_x = (X.max()+X.min()) * 0.5
            mid_y = (Y.max()+Y.min()) * 0.5
            mid_z = (Z.max()+Z.min()) * 0.5

            # Set equal limits centered around the midpoint for a correct 3D view
            self.canvas.axes.set_xlim(mid_x - max_range, mid_x + max_range)
            self.canvas.axes.set_ylim(mid_y - max_range, mid_y + max_range)
            self.canvas.axes.set_zlim(mid_z - max_range, mid_z + max_range)
        
        self.canvas.draw()
        
    # --- Weight Handling Methods ---
    def _get_default_weights(self, as_init=False):
        """
        Defines the default objective weights. 
        If as_init is True, returns defaults. Otherwise, reads values from UI inputs.
        """
        default_weights = {
            'buckling_distribution_factor': 1.0, 
            'buckling_penalty': 100.0, # High penalty for members exceeding buckling limit
            'material_usage': 1.0,
            'compressive_uniformity': 1.0,
            'average_force_magnitude': 0.0
        }
        
        if as_init:
            return default_weights
            
        # Read from UI inputs
        weights = {}
        return {
            'buckling_distribution_factor': self.weights_sliders['Buckling Distribution Factor'].value() / 100.0,
            'buckling_penalty': self.weights_sliders['Buckling Penalty'].value() / 100.0,
            'material_usage': self.weights_sliders['Material Usage'].value() / 100.0,
            'compressive_uniformity': self.weights_sliders['Compression Uniformity'].value() / 100.0,
            'average_force_magnitude': self.weights_sliders['Average Force Magnitude'].value() / 100.0,
        }
        # for key, line_edit in self.weight_inputs.items():
        #     try:
        #         # Read the text and convert to float
        #         weights[key] = float(line_edit.text())
        #     except ValueError:
        #         # Use default value if input is invalid
        #         QMessageBox.warning(self, "Invalid Input", f"Please enter a valid number for the '{key.replace('_', ' ')}' weight. Using default of {default_weights[key]}.")
        #         weights[key] = default_weights[key]

        # return weights

    # --- Event Handlers (Updated to use new weight logic) ---
    def _load_data(self):
        """Allows user to select a directory and loads the 3D truss data."""
        directory = QFileDialog.getExistingDirectory(self, "Select 3D Truss Data Directory")
        if directory:
            self.model = TrussModel()
            self.model.load_from_directory(directory)
            
            if not self.model.points.empty:
                # 1. Update status and run initial analysis
                self.status_label.setText(f"3D Truss data loaded from: {os.path.basename(directory)}")
                self.run_button.setEnabled(True)
                self.model.run_analysis()
                
                # 2. Check if the analysis produced valid results
                is_analysis_successful = self.model.is_analyzed and 'element' in self.model.stresses_df.columns
                
                self._update_points_table(self.model.points)
                self._draw_truss() # Draw the structure regardless of analysis success

                if is_analysis_successful:
                    self.status_label.setText(self.status_label.text() + " | Analysis successful.")
                    self._update_stresses_table(self.model.stresses_df)
                    
                    # Calculate initial objective for metrics table using current weights
                    initial_score, initial_metrics = get_objective(self.model, self._get_default_weights())
                    self._update_metrics_table(initial_metrics)
                else:
                    # Analysis failed (as indicated by your error message)
                    self.status_label.setText(self.status_label.text() + " | **3D Truss Analysis FAILED.** See console for details.")
                    self._update_stresses_table(pd.DataFrame()) # Show error message in the stresses table
                    self._update_metrics_table({'Total Score': 'N/A', 'Status': 'Analysis Failed'})
                    self.run_button.setEnabled(False) # Optimization relies on a successful analysis
                
            else:
                self.status_label.setText("Failed to load data. Check console for errors.")
                self.run_button.setEnabled(False)

    def _run_optimization(self):
        """Executes the 3D optimization process."""
        if self.model is None or self.model.points.empty:
            QMessageBox.warning(self, "Error", "No 3D truss data loaded.")
            return

        self.run_button.setEnabled(False)
        self.status_label.setText("Running 3D optimization... Please wait.")
        QApplication.processEvents() # Update GUI
        
        # Get weights from UI before starting optimization
        weights = self._get_default_weights() 
        
        # Identify nodes to optimize (not fully supported)
        # fixed_condition = (self.model.supports['x'] == 1) & (self.model.supports['y'] == 1)
        # if 'z' in self.model.supports.columns:
        #     fixed_condition &= (self.model.supports['z'] == 1)

        # supported_nodes = self.model.supports[fixed_condition]['Node'].tolist()
        
        # all_nodes = self.model.points['Node'].tolist()
        
        # # Only optimize nodes that are not fully fixed
        # nodes_to_optimize = [n for n in all_nodes if n not in supported_nodes]
        
        # if not nodes_to_optimize:
        #      self.status_label.setText("No free nodes to optimize. Optimization aborted.")
        #      self.run_button.setEnabled(True)
        #      return
        selected_rows = self.points_table.selectionModel().selectedRows()
        nodes_to_optimize = [int(self.points_table.item(row.row(), 0).text().split(sep='.')[0]) for row in selected_rows]
        
        # NOTE: The current optimizer is designed for 2D. You may need to adapt 
        # optimizer.py's update_node_positions call to include the Z dimension 
        # if you want true 3D optimization. For now, it might only optimize X/Y.

        optimized_model, final_score, final_metrics = optimize_truss(
            self.model, nodes_to_optimize, weights
        )
        self.model = optimized_model

        # Save the optimized points to the output directory
        output_file = os.path.join(self.output_dir, f"optimized_points_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        self.model.points.to_csv(output_file, index=False)
        
        self.status_label.setText(f"Optimization complete! Final Score: {final_score:.4f}")
        self._update_metrics_table(final_metrics)
        self._update_points_table(self.model.points)
        self._update_stresses_table(self.model.stresses_df)
        self._draw_truss()
        
        self.run_button.setEnabled(True)

    def closeEvent(self, event):
        """
        Overrides the default close behavior to ensure the object is
        deleted when closed, which triggers the QObject.destroyed signal.
        """
        # This is the line that makes the difference
        self.deleteLater()
        
        # Proceed with the close event
        event.accept()

# --- Refactored Entry Point for Unified Compilation ---
def main():
    """
    Stand-alone execution entry point. 
    Returns the window instance if called by the launcher.
    """
    app = QApplication.instance()
    is_standalone = False
    if app is None:
        app = QApplication(sys.argv)
        is_standalone = True

    window = OptimizerApp()
    window.show()

    if is_standalone:
        sys.exit(app.exec())
        
    return window
