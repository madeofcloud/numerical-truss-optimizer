import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTableWidget, QTableWidgetItem, QAbstractItemView,
                             QMessageBox, QSlider, QTabWidget, QGridLayout, QFrame,
                             QFileDialog)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D

# This import assumes the other files are in the same directory
from truss_analysis import load_truss_data, get_objective, run_truss_simulation
from optimizer import optimize_truss
from truss_solver import truss_analyze
import csv

class MplCanvas(FigureCanvas):
    """A custom class to embed a Matplotlib figure into a PyQt widget."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)


class Mpl3DCanvas(FigureCanvas):
    """A custom class to embed a 3D Matplotlib figure into a PyQt widget."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111, projection='3d')
        super(Mpl3DCanvas, self).__init__(self.fig)
        self.setParent(parent)


class MainWindow(QMainWindow):
    """Main application window for the truss optimizer."""
    def __init__(self):
        super().__init__()
        
        self.current_data_dir = ""
        self.data = {}
        self.setWindowTitle("Truss Optimizer & Analysis")
        self.setGeometry(100, 100, 1400, 900)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QHBoxLayout(self.central_widget)
        self.create_control_panel()
        self.create_visualization_panel()
        
        # Create a directory for outputs
        self.output_dir = os.path.join(os.getcwd(), 'output', datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Initial status
        self.status_label.setText("Please select a design directory.")

    def create_control_panel(self):
        """Creates the control panel on the left side of the UI."""
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_layout.setAlignment(Qt.AlignTop)

        # Design Selection
        design_group = QFrame()
        design_layout = QVBoxLayout(design_group)
        design_group.setFrameShape(QFrame.StyledPanel)
        design_layout.addWidget(QLabel("<b>Design Selection</b>"))
        
        path_layout = QHBoxLayout()
        self.path_line_edit = QLineEdit(self.current_data_dir)
        self.path_line_edit.setReadOnly(True)
        self.path_line_edit.setMaximumWidth(200) # Set a conservative max length
        path_layout.addWidget(self.path_line_edit)
        
        select_button = QPushButton("Select Directory...")
        select_button.clicked.connect(self.select_design_directory)
        path_layout.addWidget(select_button)
        design_layout.addLayout(path_layout)

        control_layout.addWidget(design_group)

        # Optimization Parameters
        param_group = QFrame()
        param_layout = QGridLayout(param_group)
        param_group.setFrameShape(QFrame.StyledPanel)
        param_layout.addWidget(QLabel("<b>Optimization Weights</b>"), 0, 0, 1, 2)

        self.weights_sliders = {}
        row = 1
        
        # Define sliders with their tooltips and initial values, based on SSA 7 objectives
        sliders_config = [
            ("Buckling Distribution Factor", 25.0, "Weight for the Buckling Distribution Factor ($O_d = \gamma+2s_{\mu}$). Lower values prioritize safety."),
            ("Buckling Penalty", 100.0, "Weight for the Buckling Failure Penalty ($O_b$). A very high value ensures the optimizer avoids any design that causes $\mu_i \ge 1$."),
            ("Material Cost", 50.0, "Weight for the Material Cost ($O_m = \sum A_i L_i$). Higher values prioritize lighter designs."),
            ("Compression Uniformity", 10.0, "Weight for the Compression Uniformity ($O_u = s_{\mu}/\gamma$)."),
            ("Average Force Magnitude", 40, "Weight for the Average Magnitude of Internal Forces ($O_a$). Higher values prioritize designs that minimize overall internal loading."),
        ]
        
        for name, initial_value, tooltip in sliders_config:
            label = QLabel(name)
            slider = QSlider(Qt.Horizontal)
            slider.setRange(0, 10000)
            slider.setValue(int(initial_value*100))
            slider.setSingleStep(1)
            slider.setToolTip(tooltip)
            
            value_label = QLabel(f"{initial_value:.2f}")
            slider.valueChanged.connect(lambda value, vl=value_label: vl.setText(f"{value/100:.2f}"))

            param_layout.addWidget(label, row, 0)
            param_layout.addWidget(slider, row, 1)
            param_layout.addWidget(value_label, row, 2)
            self.weights_sliders[name] = slider
            row += 1

        control_layout.addWidget(param_group)

        # Nodes to Optimize
        node_group = QFrame()
        node_layout = QVBoxLayout(node_group)
        node_group.setFrameShape(QFrame.StyledPanel)
        node_layout.addWidget(QLabel("<b>Nodes to Optimize</b>"))
        
        self.node_table = QTableWidget()
        self.node_table.setColumnCount(1)
        self.node_table.setHorizontalHeaderLabels(['Node ID'])
        self.node_table.setSelectionMode(QAbstractItemView.MultiSelection)
        self.node_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        node_layout.addWidget(self.node_table)
        control_layout.addWidget(node_group)

        # Run Button
        self.run_button = QPushButton("Run Optimization")
        self.run_button.clicked.connect(self.run_optimization)
        self.run_button.setEnabled(False)  # Disable until data is loaded
        control_layout.addWidget(self.run_button)

        # Add a placeholder for a status label
        self.status_label = QLabel("Ready.")
        self.status_label.setWordWrap(True) # Make sure the text wraps
        control_layout.addWidget(self.status_label)

        self.main_layout.addWidget(control_panel)

    def create_visualization_panel(self):
        """Creates the visualization panel on the right side of the UI."""
        viz_panel = QWidget()
        viz_layout = QVBoxLayout(viz_panel)

        self.tab_widget = QTabWidget()
        
        # 2D Truss Plot
        self.truss_canvas = MplCanvas()
        self.tab_widget.addTab(self.truss_canvas, "2D Truss")
        
        # Metrics Table
        self.metrics_table = QTableWidget()
        self.metrics_table.setColumnCount(2)
        self.metrics_table.setHorizontalHeaderLabels(['Metric', 'Value'])
        self.tab_widget.addTab(self.metrics_table, "Metrics")
        
        # Final Positions Table
        self.final_points_table = QTableWidget()
        self.final_points_table.setColumnCount(3)
        self.final_points_table.setHorizontalHeaderLabels(['Node ID', 'x', 'y'])
        self.tab_widget.addTab(self.final_points_table, "Final Positions")

        viz_layout.addWidget(self.tab_widget)
        self.main_layout.addWidget(viz_panel)

    def select_design_directory(self):
        """Opens a directory selector dialog and loads the selected data."""
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.Directory)
        
        if dialog.exec_():
            selected_dir = dialog.selectedFiles()[0]
            self.current_data_dir = selected_dir
            self.path_line_edit.setText(self.current_data_dir)
            self.load_data_and_refresh_ui()

    def load_data_and_refresh_ui(self):
        """Loads data from the current directory and refreshes the UI."""
        try:
            points_path = os.path.join(self.current_data_dir, "points.csv")
            trusses_path = os.path.join(self.current_data_dir, "trusses.csv")
            supports_path = os.path.join(self.current_data_dir, "supports.csv")
            materials_path = os.path.join(self.current_data_dir, "materials.csv")
            loads_path = os.path.join(self.current_data_dir, "loads.csv")
            
            # Use os.path.exists to check if loads.csv exists
            loads_data = loads_path if os.path.exists(loads_path) else None
            
            self.data = load_truss_data(points_path, trusses_path, supports_path, materials_path, loads_data)
            
            # Refresh the nodes table
            self.node_table.setRowCount(self.data['points'].shape[0])
            for i, node_id in enumerate(self.data['points']['Node']):
                self.node_table.setItem(i, 0, QTableWidgetItem(str(node_id)))
            
            # Refresh visualization
            self.show_truss(self.data)
            self.update_metrics_table({})
            self.update_points_table(pd.DataFrame()) # Pass an empty DataFrame
            
            self.status_label.setText(f"Loaded design from: {self.current_data_dir}")
            self.run_button.setEnabled(True)
            
        except FileNotFoundError as e:
            self.status_label.setText(f"Error: File not found in directory: {e.filename}")
            QMessageBox.warning(self, "Error", f"File not found: {e.filename}. Please ensure all required CSV files are in the selected folder.")
            self.run_button.setEnabled(False)


    def show_truss(self, data):
        """
        Draws the truss diagram and forces on the MplCanvas.
        Automatically scales force arrows.
        """
        self.truss_canvas.axes.clear()
        
        points_df = data['points']
        trusses_df = data['trusses']
        supports_df = data['supports']
        
        # Get the displacements and stresses to display member forces
        try:
            stresses_df, displacements = run_truss_simulation(data)
        except Exception as e:
            print(f"⚠️ Truss simulation failed: {e}")
            stresses_df = pd.DataFrame(columns=['element', 'axial_force'])
            displacements = None

        # Plot members
        for _, row in trusses_df.iterrows():
            p1 = points_df.loc[points_df['Node'] == row['start'], ['x', 'y']].values[0]
            p2 = points_df.loc[points_df['Node'] == row['end'], ['x', 'y']].values[0]

            try:
                force_row = stresses_df.loc[stresses_df['element'] == row['element'], 'axial_force']
                if not force_row.empty:
                    force = force_row.iloc[0]
                    color = 'red' if force < 0 else 'blue'
                else:
                    force = None
                    color = 'gray'  # fallback color if no force calculated
            except Exception as e:
                print(f"⚠️ Could not retrieve force for element {row['element']}: {e}")
                force = None
                color = 'gray'
            
            self.truss_canvas.axes.plot([p1[0], p2[0]], [p1[1], p2[1]], color=color)

        # Plot nodes and labels
        self.truss_canvas.axes.plot(points_df['x'], points_df['y'], 'o', color='black')
        for _, row in points_df.iterrows():
            self.truss_canvas.axes.text(row['x'] + 0.05, row['y'] + 0.05, str(int(row['Node'])), 
                                        ha='left', va='bottom', fontsize=8)

        # Plot supports
        for _, row in supports_df.iterrows():
            node_pos = points_df.loc[points_df['Node'] == row['Node'], ['x', 'y']].values[0]
            self.truss_canvas.axes.plot(node_pos[0], node_pos[1], 's', color='green', markersize=10)
            
        # Plot loads as arrows
        if data['loads'] is not None:
            max_truss_span = max(points_df['x'].max() - points_df['x'].min(), 
                                points_df['y'].max() - points_df['y'].min())
            arrow_scale = max_truss_span * 0.1  # Scale arrows to 10% of the truss's largest dimension
            
            for _, row in data['loads'].iterrows():
                node_pos = points_df.loc[points_df['Node'] == row['Node'], ['x', 'y']].values[0]
                fx, fy = row['Fx'], row['Fy']
                
                # Normalize the force vector to get a consistent arrow size
                force_magnitude = np.sqrt(fx**2 + fy**2)
                if force_magnitude > 0:
                    unit_fx, unit_fy = fx / force_magnitude, fy / force_magnitude
                    self.truss_canvas.axes.arrow(
                        node_pos[0], node_pos[1], 
                        unit_fx * arrow_scale, unit_fy * arrow_scale,
                        head_width=0.05 * arrow_scale, head_length=0.1 * arrow_scale, fc='purple', ec='purple'
                    )

        self.truss_canvas.axes.set_title("Truss Diagram")
        self.truss_canvas.axes.set_xlabel("X-coordinate (m)")
        self.truss_canvas.axes.set_ylabel("Y-coordinate (m)")
        self.truss_canvas.axes.set_aspect('equal', 'box')
        self.truss_canvas.axes.grid(True)
        self.truss_canvas.draw()

        
    def update_metrics_table(self, metrics):
        """Updates the metrics table with the latest calculated values."""
        self.metrics_table.setRowCount(len(metrics))
        self.metrics_table.setHorizontalHeaderLabels(['Metric', 'Value'])
        for i, (key, value) in enumerate(metrics.items()):
            self.metrics_table.setItem(i, 0, QTableWidgetItem(key))
            if isinstance(value, (int, float, np.floating)):
                self.metrics_table.setItem(i, 1, QTableWidgetItem(f"{value:.4f}"))
            else:
                self.metrics_table.setItem(i, 1, QTableWidgetItem(str(value)))

    def update_points_table(self, points_df):
        """Updates the points table with final positions."""
        # Handle the case where the input is an empty DataFrame
        if points_df.empty:
            self.final_points_table.setRowCount(0)
            return

        self.final_points_table.setRowCount(points_df.shape[0])
        self.final_points_table.setColumnCount(3)
        self.final_points_table.setHorizontalHeaderLabels(['Node ID', 'x', 'y'])
        
        for i, row in points_df.iterrows():
            self.final_points_table.setItem(i, 0, QTableWidgetItem(str(row['Node'])))
            self.final_points_table.setItem(i, 1, QTableWidgetItem(f"{row['x']:.4f}"))
            self.final_points_table.setItem(i, 2, QTableWidgetItem(f"{row['y']:.4f}"))

    def run_optimization(self):
        """Starts the optimization process."""
        self.run_button.setEnabled(False)
        self.status_label.setText("Running optimization...")
        QApplication.processEvents()

        # Get selected nodes for optimization
        selected_rows = self.node_table.selectionModel().selectedRows()
        nodes_to_optimize = [int(self.node_table.item(row.row(), 0).text()) for row in selected_rows]
        
        if not nodes_to_optimize:
            self.status_label.setText("No nodes selected for optimization. Please select at least one node.")
            self.run_button.setEnabled(True)
            return

        # Get the weights from the sliders, mapping slider names to objective names
        weights = {
            'buckling_distribution_factor': self.weights_sliders['Buckling Distribution Factor'].value() / 100.0,
            'buckling_penalty': self.weights_sliders['Buckling Penalty'].value() / 100.0,
            'material_cost': self.weights_sliders['Material Cost'].value() / 100.0,
            'compressive_uniformity': self.weights_sliders['Compression Uniformity'].value() / 100.0,
            'average_force_magnitude': self.weights_sliders['Average Force Magnitude'].value() / 100.0,
        }
        
        # Initial analysis to show metrics before optimization
        initial_score, initial_metrics, _ = get_objective(self.data, weights)
        print("Initial Metrics:", initial_metrics)
        self.update_metrics_table(initial_metrics)
        
        # Run the optimization in a separate thread to keep the GUI responsive
        self.run_optimization_thread(nodes_to_optimize, weights)

    def run_optimization_thread(self, nodes_to_optimize, weights):
        """
        A placeholder for a threaded optimization run.
        For simplicity, we'll run it directly here, but a real app would use QThread.
        """
        optimized_data, final_score, final_metrics = optimize_truss(
            self.data, nodes_to_optimize, weights
        )

        # --- Save final optimized points to CSV ---
        output_file = os.path.join(self.output_dir, "final_points.csv")
        # Ensure 'points' is the DataFrame from the optimized_data dictionary for correct saving
        optimized_points_df = optimized_data['points']
        # The writerow assumes an iterable of values. DataFrame.values.tolist() will work.
        with open(output_file, mode="w", newline="") as f:
            writer = csv.writer(f)
            # Write header from DataFrame columns, ensuring 'Node' is first if we want it
            writer.writerow(optimized_points_df.columns.tolist())
            writer.writerows(optimized_points_df.values.tolist())

        # --- Update UI ---
        self.status_label.setText(f"Optimization complete! Final Score: {final_score:.4f}. Results saved to {output_file}")
        self.update_metrics_table(final_metrics)
        self.update_points_table(optimized_data['points'])
        self.show_truss(optimized_data)
        self.run_button.setEnabled(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())