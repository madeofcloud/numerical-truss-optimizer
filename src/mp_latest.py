import pandas as pd
import numpy as np
import sys
import os
import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTableWidget, QTableWidgetItem, QAbstractItemView,
                             QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# This import assumes truss_analysis.py is in the same directory
from truss_analysis import load_truss_data, analyze_truss, get_truss_properties

# A new, more robust objective function
def get_new_objective(truss_data, weights=[10, 0.5, 5]):
    """
    Calculates a combined objective function based on buckling, weight, and displacement.
    
    Args:
        truss_data (dict): Dictionary containing all truss dataframes.
        weights (list): A list of three floats representing the weights for each objective.
    
    Returns:
        float: The weighted sum of the objectives.
    """
    try:
        results = analyze_truss(truss_data)
        
        # 1. Buckling Objective: Minimize the maximum utilization ratio (mu)
        utilization_ratios = np.abs(results['member_forces']) / results['critical_buckling_loads']
        max_utilization = utilization_ratios.max()
        
        if max_utilization >= 1:
            # Structure has buckled, return a very large penalty value
            return 1e12

        # 2. Weight Objective: Minimize total truss weight
        total_weight = results['total_weight']
        
        # 3. Displacement Objective: Minimize the maximum node displacement
        # Find the maximum displacement across all free nodes
        displacements = results['displacements']
        if displacements.empty:
            max_displacement = 0
        else:
            max_displacement = np.sqrt(displacements['dx'].max()**2 + displacements['dy'].max()**2)
        
        # We need to scale these values to make the optimization effective.
        # Normalize by their typical ranges or simply use weights.
        
        # Combine objectives using a weighted sum
        objective_value = (weights[0] * max_utilization + 
                           weights[1] * total_weight + 
                           weights[2] * max_displacement)
        
        return objective_value
    
    except Exception as e:
        # If an error occurs (e.g., ill-conditioned matrix from a bad geometry),
        # return a large penalty value to tell the optimizer to avoid this position.
        return 1e12

class MplCanvas(FigureCanvas):
    """A custom class to embed a Matplotlib figure into a PyQt widget."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)

class ResultsWindow(QWidget):
    """A pop-up window to display the final results table."""
    def __init__(self, data_frame):
        super().__init__()
        self.setWindowTitle("Optimization Results")
        self.setGeometry(200, 200, 600, 400)
        self.layout = QVBoxLayout(self)

        self.label = QLabel("Final Optimized Node Positions:")
        self.layout.addWidget(self.label)
        
        self.table = QTableWidget()
        self.layout.addWidget(self.table)
        
        self.create_table(data_frame)

    def create_table(self, df):
        """Populates the table widget with DataFrame data."""
        if df.empty:
            msg = QMessageBox()
            msg.setWindowTitle("No Results")
            msg.setText("The optimization did not find any valid positions. The results table is empty.")
            msg.exec_()
            return

        # Correctly set the number of columns and headers
        header_labels = ["Node"] + list(df.columns)
        self.table.setColumnCount(len(header_labels))
        self.table.setHorizontalHeaderLabels(header_labels)
        self.table.setRowCount(df.shape[0])

        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setSortingEnabled(True)

        for row_idx, (node_id, row_data) in enumerate(df.iterrows()):
            # Set the node ID
            self.table.setItem(row_idx, 0, QTableWidgetItem(str(node_id)))
            # Set the x and y coordinates
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(round(row_data['x'], 4))))
            self.table.setItem(row_idx, 2, QTableWidgetItem(str(round(row_data['y'], 4))))
        
        self.table.resizeColumnsToContents()
        self.table.keyPressEvent = self.keyPressEvent_table
        
    def keyPressEvent_table(self, event):
        """Handles key presses for copy functionality."""
        if event.matches(QKeySequence.Copy):
            selected_rows = self.table.selectionModel().selectedRows()
            if not selected_rows:
                return

            clipboard_text = ""
            for row in selected_rows:
                row_data = [self.table.item(row.row(), col).text() for col in range(self.table.columnCount())]
                clipboard_text += "\t".join(row_data) + "\n"
            
            QApplication.clipboard().setText(clipboard_text.strip())

class OptimizerUI(QMainWindow):
    def __init__(self, data):
        super().__init__()
        self.data = data
        self.setWindowTitle("Truss Design Optimizer")
        self.setGeometry(100, 100, 1200, 800)

        self._main_widget = QWidget()
        self.setCentralWidget(self._main_widget)
        self._main_layout = QHBoxLayout(self._main_widget)

        # Plotting canvas
        self.truss_canvas = MplCanvas(self)
        self.truss_canvas.axes.set_aspect('equal', 'box')

        # Input and control UI on the left
        self.control_layout = QVBoxLayout()
        self.control_widget = QWidget()
        self.control_widget.setLayout(self.control_layout)
        self.control_widget.setFixedWidth(250)

        # Labels and input fields
        self.control_layout.addWidget(QLabel("Parameters:"))
        
        self.nodes_to_optimize_input = QLineEdit("6,7")
        self.control_layout.addWidget(QLabel("Nodes to Optimize (e.g., 6,7):"))
        self.control_layout.addWidget(self.nodes_to_optimize_input)

        self.iterations_input = QLineEdit("2")
        self.control_layout.addWidget(QLabel("Iterations:"))
        self.control_layout.addWidget(self.iterations_input)

        self.grid_range_input = QLineEdit("0.5")
        self.control_layout.addWidget(QLabel("Grid Search Range (+/-):"))
        self.control_layout.addWidget(self.grid_range_input)

        self.grid_steps_input = QLineEdit("10")
        self.control_layout.addWidget(QLabel("Grid Steps per Dimension:"))
        self.control_layout.addWidget(self.grid_steps_input)

        # Run button
        self.run_button = QPushButton("Run Optimization")
        self.run_button.clicked.connect(self.run_optimization)
        self.control_layout.addWidget(self.run_button)
        
        self.status_label = QLabel("Ready.")
        self.control_layout.addWidget(self.status_label)
        
        self.control_layout.addStretch()

        # Add canvases and control to main layout
        self._main_layout.addWidget(self.control_widget)
        self._main_layout.addWidget(self.truss_canvas)

        # Initial visualization
        self.visualize_truss(self.data["points"], self.data["trusses"])

    def visualize_truss(self, points, trusses, title="Truss Geometry"):
        """Updates the 2D truss plot with new node positions."""
        self.truss_canvas.axes.clear()
        self.truss_canvas.axes.set_title(title)
        self.truss_canvas.axes.set_xlabel("x-coordinate")
        self.truss_canvas.axes.set_ylabel("y-coordinate")
        self.truss_canvas.axes.set_aspect('equal', 'box')
        
        # Plot points
        self.truss_canvas.axes.plot(points['x'], points['y'], 'o', color='blue')
        
        # Add labels for each node
        for idx, row in points.iterrows():
            self.truss_canvas.axes.text(row['x'], row['y'], str(row['Node']), color='blue', ha='center', va='bottom')
            
        # Plot members
        try:
            for idx, row in trusses.iterrows():
                p1 = points[points['Node'] == row['Node1']].iloc[0]
                p2 = points[points['Node'] == row['Node2']].iloc[0]
                self.truss_canvas.axes.plot([p1['x'], p2['x']], [p1['y'], p2['y']], color='gray')
        except KeyError as e:
            self.status_label.setText(f"Error: Missing column {e} in trusses DataFrame. Check your trusses.csv file.")
            self.truss_canvas.draw()
            return
        
        self.truss_canvas.axes.grid(True)
        self.truss_canvas.draw()

    def run_optimization(self):
        """Main method to run the iterative optimization and update plots."""
        self.run_button.setEnabled(False)
        self.status_label.setText("Starting optimization...")
        
        # Create output directory
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        output_dir = f"output/multipoint_{timestamp}"
        os.makedirs(output_dir, exist_ok=True)
        
        try:
            nodes_to_optimize = [int(n) for n in self.nodes_to_optimize_input.text().split(',')]
            n_iterations = int(self.iterations_input.text())
            grid_range = float(self.grid_range_input.text())
            grid_steps = int(self.grid_steps_input.text())
        except ValueError:
            self.status_label.setText("Error: Invalid input parameters. Please enter numbers.")
            self.run_button.setEnabled(True)
            return

        current_data = self.data.copy()
        
        for i in range(n_iterations):
            self.status_label.setText(f"Iteration {i+1}/{n_iterations}...")
            self.visualize_truss(current_data["points"], current_data["trusses"], f"Iteration {i+1}: Truss Geometry")
            QApplication.processEvents()
            
            # Save a screenshot of the current iteration
            screenshot_path = os.path.join(output_dir, f"iteration_{i+1}.png")
            self.truss_canvas.fig.savefig(screenshot_path)
            print(f"Saved screenshot to {screenshot_path}")

            for node_id in nodes_to_optimize:
                self.status_label.setText(f"Optimizing node {node_id}...")
                QApplication.processEvents()

                # Get the current position
                x0 = current_data["points"].loc[current_data["points"]['Node'] == node_id, 'x'].values[0]
                y0 = current_data["points"].loc[current_data["points"]['Node'] == node_id, 'y'].values[0]
                
                # Define the grid search space
                x_coords = np.linspace(x0 - grid_range, x0 + grid_range, grid_steps)
                y_coords = np.linspace(y0 - grid_range, y0 + grid_range, grid_steps)

                best_objective = 1e12
                best_pos = (x0, y0)

                # Reverted to a simple nested loop for grid search
                for x in x_coords:
                    for y in y_coords:
                        temp_data = current_data.copy()
                        temp_data["points"].loc[temp_data["points"]['Node'] == node_id, 'x'] = x
                        temp_data["points"].loc[temp_data["points"]['Node'] == node_id, 'y'] = y
                        
                        try:
                            # Use the new, more robust objective function
                            obj_value = get_new_objective(temp_data)
                            if obj_value < best_objective:
                                best_objective = obj_value
                                best_pos = (x, y)
                        except Exception:
                            # Skip if the structure collapses or an error occurs
                            continue
                            
                if best_objective < 1e12:
                    new_x, new_y = best_pos
                    current_data["points"].loc[current_data["points"]['Node'] == node_id, 'x'] = new_x
                    current_data["points"].loc[current_data["points"]['Node'] == node_id, 'y'] = new_y
                    self.status_label.setText(f"Node {node_id} optimized. New objective: {best_objective:.4f}")
                else:
                    self.status_label.setText(f"Grid search failed for node {node_id}.")
                
                QApplication.processEvents()
        
        self.status_label.setText("Optimization Complete. Saving results...")
        
        # Combine original data with final optimized points
        final_points = self.data["points"].copy()
        for node_id in nodes_to_optimize:
            final_points.loc[final_points['Node'] == node_id, 'x'] = current_data["points"].loc[current_data["points"]['Node'] == node_id, 'x'].values[0]
            final_points.loc[final_points['Node'] == node_id, 'y'] = current_data["points"].loc[current_data["points"]['Node'] == node_id, 'y'].values[0]

        # Save the final combined DataFrame to a CSV file
        csv_path = os.path.join(output_dir, "final_positions.csv")
        final_points.to_csv(csv_path, index=False)
        print(f"Saved final positions to {csv_path}")

        self.visualize_truss(current_data["points"], current_data["trusses"], "Final Optimized Truss Geometry")
        self.run_button.setEnabled(True)

        final_positions = current_data["points"].set_index('Node').loc[nodes_to_optimize, ['x', 'y']].copy()
        
        self.results_window = ResultsWindow(final_positions)
        self.results_window.show()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Load data once at the start
    try:
        data = load_truss_data(
            "data/design_3/points.csv",
            "data/design_3/trusses.csv",
            "data/design_3/supports.csv",
            "data/design_3/materials.csv",
            loads_csv="data/design_3/loads.csv"
        )
    except FileNotFoundError as e:
        print(f"Error: Required CSV file not found: {e}")
        sys.exit(1)

    window = OptimizerUI(data)
    window.show()
    sys.exit(app.exec_())
