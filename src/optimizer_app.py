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
                             QFileDialog, QSplitter)
from PySide6.QtCore import Qt

# Refactored project imports
from ui_themes import LIGHT_THEME, DARK_THEME
from ui_components import MplCanvas
from truss_model import TrussModel
from optimizer import optimize_truss
from analysis import get_objective

class OptimizerApp(QMainWindow):
    """Main application window for the truss optimizer."""
    def __init__(self):
        super().__init__()
        
        self.model = None
        self.current_theme = "dark"
        
        self.setWindowTitle("Truss Optimizer & Analysis")
        self.setGeometry(100, 100, 1400, 900)

        # Create a directory for outputs
        self.output_dir = os.path.join(os.getcwd(), 'output', datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QHBoxLayout(self.central_widget)
        self.splitter = QSplitter(Qt.Horizontal)
        self.main_layout.addWidget(self.splitter)

        self.control_panel = self._create_control_panel()
        self.viz_panel = self._create_visualization_panel()

        self.splitter.addWidget(self.control_panel)
        self.splitter.addWidget(self.viz_panel)
        self.splitter.setSizes([420, 980])
        self.splitter.setStretchFactor(1, 1)

        self.apply_theme("dark")
        self.status_label.setText("Please select a design directory.")

    def _create_control_panel(self):
        """Creates the left-side control panel."""
        panel = QFrame()
        panel.setMinimumWidth(380)
        panel.setMaximumWidth(480)
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignTop)

        # Theme Toggle
        self.theme_button = QPushButton("🌙 Dark Mode")
        self.theme_button.clicked.connect(self.toggle_theme)
        layout.addWidget(self.theme_button, alignment=Qt.AlignRight)

        # Design Selection
        design_group = QFrame()
        design_layout = QVBoxLayout(design_group)
        design_layout.addWidget(QLabel("<b>Design Selection</b>"))
        path_layout = QHBoxLayout()
        self.path_line_edit = QLineEdit()
        self.path_line_edit.setReadOnly(True)
        path_layout.addWidget(self.path_line_edit)
        select_button = QPushButton("Select...")
        select_button.clicked.connect(self.select_design_directory)
        path_layout.addWidget(select_button)
        design_layout.addLayout(path_layout)
        layout.addWidget(design_group)

        # Optimization Weights
        param_group = QFrame()
        param_layout = QGridLayout(param_group)
        param_layout.addWidget(QLabel("<b>Optimization Weights</b>"), 0, 0, 1, 3)
        self.weights_sliders = {}
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
        layout.addWidget(param_group)

        # Nodes to Optimize
        node_group = QFrame()
        node_layout = QVBoxLayout(node_group)
        node_layout.addWidget(QLabel("<b>Nodes to Optimize</b>"))
        self.node_table = QTableWidget(0, 1)
        self.node_table.setHorizontalHeaderLabels(['Node ID'])
        self.node_table.setSelectionMode(QAbstractItemView.MultiSelection)
        self.node_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        node_layout.addWidget(self.node_table)
        layout.addWidget(node_group)

        # Run Button and Status
        self.run_button = QPushButton("Run Optimization")
        self.run_button.clicked.connect(self.run_optimization)
        self.run_button.setEnabled(False)
        layout.addWidget(self.run_button)
        self.status_label = QLabel("Ready.")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        layout.addStretch()
        return panel

    def _create_visualization_panel(self):
        """Creates the right-side visualization panel."""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        self.tab_widget = QTabWidget()
        
        self.truss_canvas = MplCanvas()
        self.metrics_table = QTableWidget(0, 2)
        self.metrics_table.setHorizontalHeaderLabels(['Metric', 'Value'])
        self.final_points_table = QTableWidget(0, 3)
        self.final_points_table.setHorizontalHeaderLabels(['Node ID', 'x', 'y'])
        
        self.tab_widget.addTab(self.truss_canvas, "2D Truss Plot")
        self.tab_widget.addTab(self.metrics_table, "Metrics")
        self.tab_widget.addTab(self.final_points_table, "Final Positions")
        layout.addWidget(self.tab_widget)
        return panel

    def toggle_theme(self):
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme(self.current_theme)

    def apply_theme(self, theme_name):
        self.setStyleSheet(LIGHT_THEME if theme_name == "light" else DARK_THEME)
        self.theme_button.setText("🌞 Light Mode" if theme_name == "dark" else "🌙 Dark Mode")
        self._apply_matplotlib_theme(theme_name)

    def _apply_matplotlib_theme(self, theme_name):
        is_dark = theme_name == "dark"
        bg_color = "#2b2b2b" if is_dark else "#ffffff"
        fg_color = "white" if is_dark else "black"
        
        self.truss_canvas.fig.patch.set_facecolor(bg_color)
        ax = self.truss_canvas.axes
        ax.set_facecolor(bg_color)
        ax.tick_params(colors=fg_color, which="both")
        for spine in ax.spines.values(): spine.set_color(fg_color)
        ax.xaxis.label.set_color(fg_color)
        ax.yaxis.label.set_color(fg_color)
        ax.title.set_color(fg_color)
        self.truss_canvas.draw()
        
    def select_design_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Design Directory")
        if directory:
            self.path_line_edit.setText(directory)
            self.model = TrussModel()
            success, message = self.model.load_from_directory(directory)
            if success:
                self.status_label.setText(f"Loaded: {os.path.basename(directory)}")
                self.run_button.setEnabled(True)
                self._refresh_ui_from_model()
            else:
                QMessageBox.warning(self, "Error", message)
                self.run_button.setEnabled(False)

    def _refresh_ui_from_model(self):
        """Updates all UI elements based on the current self.model state."""
        if not self.model: return
        
        self.node_table.setRowCount(0)
        for node_id in self.model.points['Node']:
            row_pos = self.node_table.rowCount()
            self.node_table.insertRow(row_pos)
            self.node_table.setItem(row_pos, 0, QTableWidgetItem(str(node_id)))

        _, metrics = get_objective(self.model, self._get_weights())
        self._update_metrics_table(metrics)
        self._update_points_table(self.model.points)
        self._draw_truss()
        
    def _draw_truss(self):
        """Draws the current truss from self.model on the canvas using the original robust logic."""
        if not self.model: return
        
        ax = self.truss_canvas.axes
        ax.clear()
        
        points_df = self.model.points
        trusses_df = self.model.trusses
        stresses_df = self.model.stresses_df
        supports_df = self.model.supports
        loads_df = self.model.loads

        # Plot members
        for _, row in trusses_df.iterrows():
            p1 = points_df.loc[points_df['Node'] == row['start'], ['x', 'y']].values[0]
            p2 = points_df.loc[points_df['Node'] == row['end'], ['x', 'y']].values[0]
            
            # Safely get force and determine color
            try:
                force_row = stresses_df.loc[stresses_df['element'] == row['element'], 'axial_force']
                if not force_row.empty:
                    force = force_row.iloc[0]
                    # Original used red for compression, blue for tension
                    color = 'red' if force < 0 else 'blue'
                else:
                    color = 'gray'
            except (KeyError, IndexError):
                color = 'gray'
            
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=color)

        # Plot nodes and labels
        ax.plot(points_df['x'], points_df['y'], 'o', color='black')
        for _, row in points_df.iterrows():
            ax.text(row['x'] + 0.05, row['y'] + 0.05, str(int(row['Node'])), 
                    ha='left', va='bottom', fontsize=8)

        # Plot supports
        for _, row in supports_df.iterrows():
            node_pos = points_df.loc[points_df['Node'] == row['Node'], ['x', 'y']].values[0]
            ax.plot(node_pos[0], node_pos[1], 's', color='green', markersize=10)
            
        # Plot loads with dynamic arrow scaling
        if loads_df is not None and not loads_df.empty:
            max_truss_span = max(points_df['x'].max() - points_df['x'].min(), 
                                points_df['y'].max() - points_df['y'].min())
            # Avoid division by zero if truss is a single point
            if max_truss_span > 0:
                arrow_scale = max_truss_span * 0.1
                
                for _, row in loads_df.iterrows():
                    node_pos = points_df.loc[points_df['Node'] == row['Node'], ['x', 'y']].values[0]
                    fx, fy = row['Fx'], row['Fy']
                    
                    force_magnitude = np.sqrt(fx**2 + fy**2)
                    if force_magnitude > 0:
                        unit_fx, unit_fy = fx / force_magnitude, fy / force_magnitude
                        ax.arrow(
                            node_pos[0], node_pos[1], 
                            unit_fx * arrow_scale, unit_fy * arrow_scale,
                            head_width=0.05 * arrow_scale, head_length=0.1 * arrow_scale, 
                            fc='purple', ec='purple'
                        )

        ax.set_title("Truss Diagram")
        ax.set_xlabel("X-coordinate (m)")
        ax.set_ylabel("Y-coordinate (m)")
        ax.set_aspect('equal', 'box')
        ax.grid(True)
        self.truss_canvas.fig.tight_layout()
        self.truss_canvas.draw()
        
    def _update_metrics_table(self, metrics):
        self.metrics_table.setRowCount(len(metrics))
        for i, (key, value) in enumerate(metrics.items()):
            self.metrics_table.setItem(i, 0, QTableWidgetItem(key))
            self.metrics_table.setItem(i, 1, QTableWidgetItem(f"{value:.4f}"))
        self.metrics_table.resizeColumnsToContents()

    def _update_points_table(self, points_df):
        self.final_points_table.setRowCount(points_df.shape[0])
        for i, row in points_df.iterrows():
            self.final_points_table.setItem(i, 0, QTableWidgetItem(str(row['Node'])))
            self.final_points_table.setItem(i, 1, QTableWidgetItem(f"{row['x']:.4f}"))
            self.final_points_table.setItem(i, 2, QTableWidgetItem(f"{row['y']:.4f}"))
        self.final_points_table.resizeColumnsToContents()

    def _get_weights(self):
        return {
            'buckling_distribution_factor': self.weights_sliders['Buckling Distribution Factor'].value() / 100.0,
            'buckling_penalty': self.weights_sliders['Buckling Penalty'].value() / 100.0,
            'material_usage': self.weights_sliders['Material Usage'].value() / 100.0,
            'compressive_uniformity': self.weights_sliders['Compression Uniformity'].value() / 100.0,
            'average_force_magnitude': self.weights_sliders['Average Force Magnitude'].value() / 100.0,
        }
        
    def run_optimization(self):
        if not self.model: return
        
        selected_rows = self.node_table.selectionModel().selectedRows()
        nodes_to_optimize = [int(self.node_table.item(row.row(), 0).text()) for row in selected_rows]
        
        if not nodes_to_optimize:
            QMessageBox.warning(self, "Warning", "Please select at least one node to optimize.")
            return

        self.run_button.setEnabled(False)
        self.status_label.setText("Running optimization...")
        QApplication.processEvents()

        weights = self._get_weights()
        
        optimized_model, final_score, final_metrics = optimize_truss(
            self.model, nodes_to_optimize, weights
        )
        self.model = optimized_model

        output_file = os.path.join(self.output_dir, "final_points.csv")
        self.model.points.to_csv(output_file, index=False)
        
        self.status_label.setText(f"Optimization complete! Final Score: {final_score:.4f}")
        self._update_metrics_table(final_metrics)
        self._update_points_table(self.model.points)
        self._draw_truss()
        
        self.run_button.setEnabled(True)
    pass

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

    # Use the renamed class
    window = OptimizerApp() 
    
    if is_standalone:
        window.show()
        sys.exit(app.exec())
    
    return window

if __name__ == '__main__':
    main()