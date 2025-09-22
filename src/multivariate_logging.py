import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton,
                             QTableWidget, QTableWidgetItem, QAbstractItemView,
                             QMessageBox)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QKeySequence
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D

# This import assumes truss_analysis.py is in the same directory
from truss_analysis import load_truss_data, vary_node_position, get_objective


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
            # Set the x coordinate
            self.table.setItem(row_idx, 1, QTableWidgetItem(str(round(row_data['x'], 4))))
            # Set the y coordinate
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
        
        # Folder for output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.output_dir = f"output/multipoint_{timestamp}"
        os.makedirs(self.output_dir, exist_ok=True)
        print(f"Output will be saved to: {self.output_dir}")

        self._main_widget = QWidget()
        self.setCentralWidget(self._main_widget)
        self._main_layout = QHBoxLayout(self._main_widget)

        # Plotting canvases
        self.truss_canvas = MplCanvas(self)
        self.truss_canvas.axes.set_aspect('equal', 'box')
        self.surface_canvas = Mpl3DCanvas(self)

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

        self.grid_points_input = QLineEdit("5")
        self.control_layout.addWidget(QLabel("Grid Points:"))
        self.control_layout.addWidget(self.grid_points_input)

        self.delta_input = QLineEdit("0.1")
        self.control_layout.addWidget(QLabel("Delta:"))
        self.control_layout.addWidget(self.delta_input)
        
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
        self._main_layout.addWidget(self.surface_canvas)

        # Initial visualization
        self.visualize_truss(self.data["points"], self.data["trusses"])
        self.surface_canvas.axes.set_title("3D Objective Surface")
        self.surface_canvas.draw()

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
                p1 = points[points['Node'] == row['start']].iloc[0]
                p2 = points[points['Node'] == row['end']].iloc[0]
                self.truss_canvas.axes.plot([p1['x'], p2['x']], [p1['y'], p2['y']], color='gray')
        except KeyError as e:
            self.status_label.setText(f"Error: Missing column {e} in trusses DataFrame. Check your trusses.csv file.")
            self.truss_canvas.draw()
            return
        
        self.truss_canvas.axes.grid(True)
        self.truss_canvas.draw()

    def plot_surface(self, results_df, node_id):
        """Updates the 3D surface plot with new data."""
        self.surface_canvas.axes.clear()
        self.surface_canvas.axes.set_title(f"Objective vs Node {node_id} Position")
        self.surface_canvas.axes.set_xlabel("x-position")
        self.surface_canvas.axes.set_ylabel("y-position")
        self.surface_canvas.axes.set_zlabel("Buckling Factor")

        plot_df = results_df.dropna(subset=["objective"]).drop_duplicates(subset=["x", "y"])
        if len(plot_df) >= 3:
            try:
                self.surface_canvas.axes.plot_trisurf(plot_df["x"], plot_df["y"], plot_df["objective"],
                                                      cmap="viridis", edgecolor="none")
            except Exception as e:
                self.status_label.setText(f"Error plotting 3D surface for node {node_id}: {e}")
                
        self.surface_canvas.draw()

    def run_optimization(self):
        """Main method to run the iterative optimization and update plots."""
        self.run_button.setEnabled(False)
        self.status_label.setText("Starting optimization...")
        
        try:
            nodes_to_optimize = [int(n) for n in self.nodes_to_optimize_input.text().split(',')]
            n_iterations = int(self.iterations_input.text())
            n_grid_points = int(self.grid_points_input.text())
            delta = float(self.delta_input.text())
        except ValueError:
            self.status_label.setText("Error: Invalid input parameters. Please enter numbers.")
            self.run_button.setEnabled(True)
            return

        current_data = self.data.copy()
        
        for i in range(n_iterations):
            self.status_label.setText(f"Iteration {i+1}/{n_iterations}...")
            self.visualize_truss(current_data["points"], current_data["trusses"], f"Iteration {i+1}: Truss Geometry")
            QApplication.processEvents()

            # Save screenshot of the truss plot
            truss_screenshot_path = os.path.join(self.output_dir, f"truss_iteration_{i+1}.png")
            self.truss_canvas.fig.savefig(truss_screenshot_path)
            print(f"Saved screenshot: {truss_screenshot_path}")

            for node_id in nodes_to_optimize:
                self.status_label.setText(f"Optimizing node {node_id}...")
                QApplication.processEvents()
                
                x0 = current_data["points"].loc[current_data["points"]['Node'] == node_id, 'x'].values[0]
                y0 = current_data["points"].loc[current_data["points"]['Node'] == node_id, 'y'].values[0]
                
                x_positions = np.linspace(x0 - delta, x0 + delta, n_grid_points)
                y_positions = np.linspace(y0 - delta, y0 + delta, n_grid_points)

                results_df = vary_node_position(
                    current_data,
                    node_to_move=node_id,
                    x_positions=x_positions,
                    y_positions=y_positions,
                    objective_fn=get_objective,
                    plot=False # We handle plotting in the GUI
                )
                
                self.plot_surface(results_df, node_id)
                QApplication.processEvents()

                if not results_df['objective'].isnull().all():
                    min_obj_row = results_df.loc[results_df['objective'].idxmin()]
                    new_x = min_obj_row['x']
                    new_y = min_obj_row['y']
                    current_data["points"].loc[current_data["points"]['Node'] == node_id, 'x'] = new_x
                    current_data["points"].loc[current_data["points"]['Node'] == node_id, 'y'] = new_y
                else:
                    self.status_label.setText(f"Node {node_id}: No valid positions found. Skipping.")
                    QApplication.processEvents()
        
        self.status_label.setText("Optimization Complete.")
        self.visualize_truss(current_data["points"], current_data["trusses"], "Final Optimized Truss Geometry")
        self.run_button.setEnabled(True)

        # Save the final truss plot
        truss_screenshot_path = os.path.join(self.output_dir, "final_truss.png")
        self.truss_canvas.fig.savefig(truss_screenshot_path)
        print(f"Saved final truss screenshot: {truss_screenshot_path}")

        # Save the final points DataFrame
        final_points_path = os.path.join(self.output_dir, "final_points.csv")
        current_data["points"].to_csv(final_points_path, index=False)
        print(f"Saved final point positions to: {final_points_path}")

        final_positions = current_data["points"].set_index('Node').loc[nodes_to_optimize, ['x', 'y']].copy()
        print("\n--- Final Optimized Positions ---")
        print(final_positions)
        
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