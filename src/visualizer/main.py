import sys
import os
import numpy as np
import pandas as pd
# Convert ALL PyQt5 imports to PySide6
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QCheckBox, 
                             QLineEdit, QFileDialog, QSlider, QGridLayout, 
                             QMessageBox, QFrame, QSizePolicy, QGroupBox)
from PySide6.QtCore import Qt
# Update Matplotlib backend for PySide6/PyQt6 compatibility
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas 
from matplotlib.figure import Figure
import matplotlib.patches as patches

# --- ASSUMED EXTERNAL IMPORTS / PLACEHOLDER FUNCTIONS ---
# This assumes the function load_truss_data and run_truss_simulation are available.
try:
    from truss_analysis import load_truss_data, run_truss_simulation
except ImportError:
    # Placeholder functions if external files are not available for testing
    def load_truss_data(points_path, trusses_path, supports_path, materials_path, loads_path):
        """Mock load function for demonstration."""
        print(f"Attempting to load data from {os.path.dirname(points_path)}")
        
        # Check for required files
        for p in [points_path, trusses_path, supports_path, materials_path]:
            if not os.path.exists(p):
                raise FileNotFoundError(p)
        
        data = {}
        points_df = pd.read_csv(points_path)
        # We explicitly set Node as index here to align with expected clean data structure
        if 'Node' in points_df.columns:
            points_df = points_df.set_index('Node', drop=False)
        data['points'] = points_df
        
        data['trusses'] = pd.read_csv(trusses_path)
        data['supports'] = pd.read_csv(supports_path)
        data['materials'] = pd.read_csv(materials_path)
        data['loads'] = pd.read_csv(loads_path) if loads_path and os.path.exists(loads_path) else None
        return data
    
    def run_truss_simulation(data):
        """Mock simulation function for visualization purposes."""
        trusses_df = data['trusses'].copy()
        if 'element' in trusses_df.columns:
            if pd.api.types.is_numeric_dtype(trusses_df['element']):
                trusses_df['axial_force'] = np.where(trusses_df['element'] % 2 == 1, 1000, -1000)
            else:
                trusses_df['axial_force'] = 1000
        elif pd.api.types.is_numeric_dtype(trusses_df.index):
            trusses_df['axial_force'] = np.where(trusses_df.index % 2 == 0, 1000, -1000)
        else:
            trusses_df['axial_force'] = 1000
        return trusses_df, None 
# --------------------------------------------------------


class MplCanvas(FigureCanvas):
    """A custom class to embed a Matplotlib figure into a PyQt widget."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.default_width = width
        self.default_height = height
        self.fig = Figure(figsize=(self.default_width, self.default_height), dpi=dpi)
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)


class TrussRenderer(QMainWindow):
    """Standalone application for rendering and exporting a truss design."""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Truss Design Renderer")
        self.setGeometry(100, 100, 1000, 700)
        
        self.data = None
        self.current_data_dir = ""
        self.auto_xlim = (0, 1)
        self.auto_ylim = (0, 1)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        self.main_layout = QHBoxLayout(self.central_widget)
        
        self.create_control_panel()
        self.create_visualization_panel()
        
        self.load_data_and_refresh_ui()

    ## UI Creation Methods
    
    def create_control_panel(self):
        """Creates the control panel on the left side of the UI."""
        control_panel = QFrame()
        control_panel.setFixedWidth(280)
        control_layout = QVBoxLayout(control_panel)
        control_layout.setAlignment(Qt.AlignTop)
        control_panel.setFrameShape(QFrame.StyledPanel)
        
        # --- Design Selection ---
        design_group = QFrame()
        design_layout = QVBoxLayout(design_group)
        design_group.setFrameShape(QFrame.StyledPanel)
        design_layout.addWidget(QLabel("<b>Design Directory</b>"))
        
        path_layout = QHBoxLayout()
        self.path_line_edit = QLineEdit(self.current_data_dir)
        self.path_line_edit.setReadOnly(True)
        path_layout.addWidget(self.path_line_edit)
        
        select_button = QPushButton("Select Directory")
        select_button.clicked.connect(self.select_design_directory)
        path_layout.addWidget(select_button)
        design_layout.addLayout(path_layout)
        control_layout.addWidget(design_group)

        # -------------------------------------
        # --- Axis Limits & Aspect Ratio ---
        # -------------------------------------
        axis_group = QGroupBox("Axis Limits & Aspect")
        axis_layout = QGridLayout(axis_group)
        
        # Square Aspect Ratio Toggle
        self.square_aspect_cb = QCheckBox("Force Square Aspect Ratio (Data)")
        self.square_aspect_cb.setChecked(True)
        self.square_aspect_cb.stateChanged.connect(self.refresh_plot)
        axis_layout.addWidget(self.square_aspect_cb, 0, 0, 1, 4)

        # X-Limits
        axis_layout.addWidget(QLabel("X Min:"), 1, 0)
        self.xmin_edit = QLineEdit()
        self.xmin_edit.setToolTip("Leave blank for auto-limit.")
        self.xmin_edit.editingFinished.connect(self.refresh_plot)
        axis_layout.addWidget(self.xmin_edit, 1, 1)
        
        axis_layout.addWidget(QLabel("X Max:"), 1, 2)
        self.xmax_edit = QLineEdit()
        self.xmax_edit.setToolTip("Leave blank for auto-limit.")
        self.xmax_edit.editingFinished.connect(self.refresh_plot)
        axis_layout.addWidget(self.xmax_edit, 1, 3)

        # Y-Limits
        axis_layout.addWidget(QLabel("Y Min:"), 2, 0)
        self.ymin_edit = QLineEdit()
        self.ymin_edit.setToolTip("Leave blank for auto-limit.")
        self.ymin_edit.editingFinished.connect(self.refresh_plot)
        axis_layout.addWidget(self.ymin_edit, 2, 1)
        
        axis_layout.addWidget(QLabel("Y Max:"), 2, 2)
        self.ymax_edit = QLineEdit()
        self.ymax_edit.setToolTip("Leave blank for auto-limit.")
        self.ymax_edit.editingFinished.connect(self.refresh_plot)
        axis_layout.addWidget(self.ymax_edit, 2, 3)

        # Auto/Reset Button
        reset_limits_btn = QPushButton("Reset Limits")
        reset_limits_btn.clicked.connect(self.reset_axis_limits)
        axis_layout.addWidget(reset_limits_btn, 3, 0, 1, 4)
        
        control_layout.addWidget(axis_group)
        # -------------------------------------

        # --- Toggles and Scaling ---
        config_group = QFrame()
        config_layout = QGridLayout(config_group)
        config_group.setFrameShape(QFrame.StyledPanel)
        config_layout.addWidget(QLabel("<b>Display Options</b>"), 0, 0, 1, 3)
        
        # Row 1: Toggles
        self.show_nodes_cb = QCheckBox("Show Node IDs")
        self.show_nodes_cb.setChecked(True)
        self.show_nodes_cb.stateChanged.connect(self.refresh_plot)
        config_layout.addWidget(self.show_nodes_cb, 1, 0, 1, 3)

        self.show_trusses_cb = QCheckBox("Show Truss Element IDs")
        self.show_trusses_cb.setChecked(False)
        self.show_trusses_cb.stateChanged.connect(self.refresh_plot)
        config_layout.addWidget(self.show_trusses_cb, 2, 0, 1, 3)
        
        # Row 3: Force Scale
        config_layout.addWidget(QLabel("Force Arrow Scale"), 3, 0)
        self.scale_slider = QSlider(Qt.Horizontal)
        self.scale_slider.setRange(1, 20) 
        self.scale_slider.setValue(10)
        self.scale_slider.valueChanged.connect(self.refresh_plot)
        self.scale_label = QLabel(f"{self.scale_slider.value()/100:.2f}")
        self.scale_slider.valueChanged.connect(lambda v, vl=self.scale_label: vl.setText(f"{v/100:.2f}"))
        config_layout.addWidget(self.scale_slider, 4, 0, 1, 2)
        config_layout.addWidget(self.scale_label, 4, 2)

        # Row 5: Text Size
        config_layout.addWidget(QLabel("Label Text Size (pts)"), 5, 0)
        self.text_size_slider = QSlider(Qt.Horizontal)
        self.text_size_slider.setRange(5, 15)
        self.text_size_slider.setValue(9)
        self.text_size_slider.valueChanged.connect(self.refresh_plot)
        self.text_size_label = QLabel(f"{self.text_size_slider.value()} pts")
        self.text_size_slider.valueChanged.connect(lambda v, vl=self.text_size_label: vl.setText(f"{v} pts"))
        config_layout.addWidget(self.text_size_slider, 6, 0, 1, 2)
        config_layout.addWidget(self.text_size_label, 6, 2)
        
        # Row 7: Zoom/Padding 
        config_layout.addWidget(QLabel("Zoom/Padding"), 7, 0)
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setRange(5, 50) 
        self.zoom_slider.setValue(20) 
        self.zoom_slider.valueChanged.connect(self.refresh_plot)
        self.zoom_label = QLabel(f"{self.zoom_slider.value()}% pad")
        self.zoom_slider.valueChanged.connect(lambda v, vl=self.zoom_label: vl.setText(f"{v}% pad"))
        config_layout.addWidget(self.zoom_slider, 8, 0, 1, 2)
        config_layout.addWidget(self.zoom_label, 8, 2)

        control_layout.addWidget(config_group)

        # --- Export Button ---
        self.export_button = QPushButton("Export Plot as PNG")
        self.export_button.clicked.connect(self.export_plot)
        self.export_button.setEnabled(False)
        control_layout.addWidget(self.export_button)

        # --- Status Label ---
        self.status_label = QLabel("Ready. Select a design directory.")
        self.status_label.setWordWrap(True)
        control_layout.addWidget(self.status_label)

        control_layout.addStretch(1)
        self.main_layout.addWidget(control_panel)

    def create_visualization_panel(self):
        """Creates the main visualization area on the right side of the UI."""
        viz_panel = QWidget()
        viz_layout = QVBoxLayout(viz_panel)
        
        self.truss_canvas = MplCanvas(self, width=8, height=6)
        viz_layout.addWidget(self.truss_canvas)
        
        # --- Constraints Legend (Bottom Panel) ---
        legend_frame = QFrame()
        legend_frame.setFrameShape(QFrame.StyledPanel)
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.setAlignment(Qt.AlignCenter)
        
        def create_symbol_label(symbol, color):
            style = f"""
            QLabel {{
                background-color: transparent;
                color: {color};
                font-size: 14pt; 
                font-weight: bold;
                padding-right: 5px;
            }}
            """
            if symbol == 's': symbol_text = '■'
            elif symbol == 'D': symbol_text = '◆'
            elif symbol == 'o': symbol_text = '●'
            else: symbol_text = symbol
                
            label = QLabel(symbol_text)
            label.setStyleSheet(style)
            return label

        legend_layout.addWidget(QLabel("<b>Legend:</b>"))
        legend_layout.addWidget(create_symbol_label('s', 'green'))
        legend_layout.addWidget(QLabel("Pin/Fixed"))
        legend_layout.addWidget(create_symbol_label('D', 'darkgreen'))
        legend_layout.addWidget(QLabel("Roller"))
        
        legend_layout.addWidget(QLabel("| <b>Member Forces:</b>"))
        legend_layout.addWidget(QLabel("<span style='color:red;'>Tension (T)</span>"))
        legend_layout.addWidget(QLabel("| <span style='color:blue;'>Compression (C)</span>"))
        
        legend_layout.addWidget(QLabel("| <b>Loads:</b>"))
        legend_layout.addWidget(QLabel("<span style='color:purple;'>Applied Load</span>"))
        
        viz_layout.addWidget(legend_frame)
        self.main_layout.addWidget(viz_panel)

    ## Data Handling Methods

    def select_design_directory(self):
        """Opens a directory selector dialog and loads the selected data."""
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.Directory)
        
        if dialog.exec_():
            selected_dir = dialog.selectedFiles()[0]
            self.current_data_dir = selected_dir
            self.path_line_edit.setText(os.path.basename(self.current_data_dir))
            self.load_data_and_refresh_ui()

    def load_data_and_refresh_ui(self):
        """Loads data from the current directory and refreshes the plot."""
        if not self.current_data_dir:
            return

        try:
            points_path = os.path.join(self.current_data_dir, "points.csv")
            trusses_path = os.path.join(self.current_data_dir, "trusses.csv")
            supports_path = os.path.join(self.current_data_dir, "supports.csv")
            materials_path = os.path.join(self.current_data_dir, "materials.csv")
            loads_path = os.path.join(self.current_data_dir, "loads.csv")
            
            loads_data = loads_path if os.path.exists(loads_path) else None
            
            self.data = load_truss_data(points_path, trusses_path, supports_path, materials_path, loads_data)
            
            # --- Calculate and store auto limits ---
            points_df = self.data['points']
            if not points_df.empty and 'x' in points_df.columns and 'y' in points_df.columns:
                self.auto_xlim = (points_df['x'].min(), points_df['x'].max())
                self.auto_ylim = (points_df['y'].min(), points_df['y'].max())
                self.reset_axis_limits()
            
            self.status_label.setText(f"Loaded design: {os.path.basename(self.current_data_dir)}")
            self.export_button.setEnabled(True)
            self.refresh_plot()
            
        except FileNotFoundError as e:
            self.status_label.setText(f"Error: File not found: {os.path.basename(e.filename)}")
            QMessageBox.warning(self, "Error", f"File not found: {os.path.basename(e.filename)}. Please ensure all required CSV files are in the selected folder.")
            self.data = None
            self.export_button.setEnabled(False)
        except Exception as e:
            self.status_label.setText(f"An unexpected error occurred: {str(e)}")
            self.data = None
            self.export_button.setEnabled(False)

    def reset_axis_limits(self):
        """Resets the axis limit input fields to their auto-detected values (or empty)."""
        self.xmin_edit.setText("")
        self.xmax_edit.setText("")
        self.ymin_edit.setText("")
        self.ymax_edit.setText("")
        self.refresh_plot()

    ## Plotting and Export Methods

    def refresh_plot(self):
        """Clears the canvas and redraws the truss with current settings."""
        if self.data is not None:
            self.show_truss(self.data)

    def get_user_limits(self, points_df):
        """Reads user-defined limits from QLineEdits, falling back to stored auto limits."""
        
        min_x, max_x = self.auto_xlim
        min_y, max_y = self.auto_ylim
        
        try:
            if self.xmin_edit.text(): min_x = float(self.xmin_edit.text())
            if self.xmax_edit.text(): max_x = float(self.xmax_edit.text())

            if self.ymin_edit.text(): min_y = float(self.ymin_edit.text())
            if self.ymax_edit.text(): max_y = float(self.ymax_edit.text())
                
            return (min_x, max_x), (min_y, max_y)
            
        except ValueError:
            QMessageBox.warning(self, "Input Error", "Please enter valid numbers for axis limits.")
            return self.auto_xlim, self.auto_ylim

    def show_truss(self, data):
        """
        Draws the truss diagram, member forces, supports, and loads 
        based on current display settings, including zoom, text size, and custom limits.
        """
        if data is None or data['points'].empty:
            self.truss_canvas.fig.clf()
            self.axes = self.truss_canvas.fig.add_subplot(111)
            self.axes.set_title("No Data Loaded")
            self.axes.set_aspect('auto')
            self.truss_canvas.draw()
            return

        self.truss_canvas.fig.clf()
        self.axes = self.truss_canvas.fig.add_subplot(111)
        
        points_df = data['points']
        trusses_df = data['trusses']
        supports_df = data['supports']
        
        # --- FIX: Robust Node Coordinate Lookup ---
        is_node_indexed = points_df.index.name == 'Node'
        
        def get_node_coords(node_id):
            """Robust function to get coordinates [x, y] based on node ID."""
            try:
                if is_node_indexed:
                    # Preferred: lookup by index label (Node ID)
                    coords = points_df.loc[node_id, ['x', 'y']].values
                elif 'Node' in points_df.columns:
                    # Fallback: lookup by 'Node' column value
                    coords = points_df[points_df['Node'] == node_id][['x', 'y']].values[0]
                else:
                    # Last resort: lookup by default DataFrame index (if node_id matches the row number)
                    coords = points_df.loc[node_id, ['x', 'y']].values
                    
                # Ensure the result is a flat array of two coordinates
                return coords.flatten()
            except (KeyError, IndexError, AttributeError, ValueError):
                return None
        # ----------------------------------------

        stresses_df, _ = run_truss_simulation(data)
        text_size = self.text_size_slider.value()
        
        # Plot members
        for _, row in trusses_df.iterrows():
            p1 = get_node_coords(row['start'])
            p2 = get_node_coords(row['end'])

            if p1 is None or p2 is None: continue 
            
            force_row = stresses_df[stresses_df['element'] == row['element']]
            force = force_row['axial_force'].iloc[0] if not force_row.empty and 'axial_force' in stresses_df.columns else 0
            color = 'blue' if force < 0 else 'red' 
            
            self.axes.plot([p1[0], p2[0]], [p1[1], p2[1]], color=color, linewidth=2)
            
            # Plot truss labels if enabled
            if self.show_trusses_cb.isChecked():
                mid_x = (p1[0] + p2[0]) / 2
                mid_y = (p1[1] + p2[1]) / 2
                self.axes.text(mid_x, mid_y, str(int(row['element'])), 
                                             ha='center', va='center', fontsize=text_size-2,
                                             bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))

        # Plot nodes
        self.axes.plot(points_df['x'], points_df['y'], 'o', color='black', zorder=5, markersize=5)

        # Plot node labels if enabled
        if self.show_nodes_cb.isChecked():
            # Determine a dynamic label offset based on data span for better scaling
            span_x = self.auto_xlim[1] - self.auto_xlim[0]
            span_y = self.auto_ylim[1] - self.auto_ylim[0]
            max_span = max(span_x, span_y)
            # Use 1.5% of the largest span as the label offset distance
            label_offset_distance = max_span * 0.015 if max_span > 0 else 0.05 
            
            for index, row in points_df.iterrows():
                # Determine the Node ID: use index if it's the Node ID, otherwise use the 'Node' column
                node_id = index if is_node_indexed else row.get('Node', index) 
                
                if pd.isna(row['x']) or pd.isna(row['y']): continue
                
                # Use the calculated offset distance
                self.axes.text(row['x'] + label_offset_distance, 
                               row['y'] + label_offset_distance, 
                               str(int(node_id)), 
                               ha='left', va='bottom', fontsize=text_size, fontweight='bold', 
                               zorder=8) 


        # Plot supports
        for _, row in supports_df.iterrows():
            node_pos = get_node_coords(row['Node'])
            if node_pos is None: continue
            
            support_marker = 's'
            self.axes.plot(node_pos[0], node_pos[1], support_marker, color='green', markersize=12, zorder=6)
            
        # Plot loads as arrows
        if data['loads'] is not None and not data['loads'].empty:
            
            span_x = self.auto_xlim[1] - self.auto_xlim[0]
            span_y = self.auto_ylim[1] - self.auto_ylim[0]
            max_truss_span = max(span_x, span_y)
            if max_truss_span <= 0: max_truss_span = 1.0
            
            arrow_scale_factor = self.scale_slider.value() / 100.0 
            arrow_scale = max_truss_span * arrow_scale_factor
            
            for _, row in data['loads'].iterrows():
                node_pos = get_node_coords(row['Node'])
                if node_pos is None: continue
                    
                fx, fy = row.get('Fx', 0), row.get('Fy', 0)
                
                force_magnitude = np.sqrt(fx**2 + fy**2)
                if force_magnitude > 0:
                    unit_fx, unit_fy = fx / force_magnitude, fy / force_magnitude
                    arrow_dx = unit_fx * arrow_scale
                    arrow_dy = unit_fy * arrow_scale
                    
                    self.axes.arrow(
                        node_pos[0], node_pos[1], 
                        arrow_dx, arrow_dy,
                        head_width=0.05 * arrow_scale, head_length=0.075 * arrow_scale, 
                        fc='purple', ec='purple', linewidth=2, zorder=7
                    )
        
        # --- Apply Axis Limits, Zoom, and Aspect (Ensuring Consistent Export Aspect) ---
        
        (min_x, max_x), (min_y, max_y) = self.get_user_limits(points_df)

        span_x = max_x - min_x
        span_y = max_y - min_y
        
        padding_percent = self.zoom_slider.value() / 100.0
        
        pad_x = span_x * padding_percent / 2 if span_x > 0 else 0.5 * padding_percent
        pad_y = span_y * padding_percent / 2 if span_y > 0 else 0.5 * padding_percent
        
        self.axes.set_xlim(min_x - pad_x, max_x + pad_x)
        self.axes.set_ylim(min_y - pad_y, max_y + pad_y)

        # Set Aspect Ratio and adjust Figure size for consistent export
        if self.square_aspect_cb.isChecked():
            self.axes.set_aspect('equal', 'box') 
            
            total_span_x = (max_x + pad_x) - (min_x - pad_x)
            total_span_y = (max_y + pad_y) - (min_y - pad_y)

            if total_span_x > 0 and total_span_y > 0:
                # Use a standard figure width (e.g., 8 inches) and calculate the height
                new_fig_width = 8.0 
                new_fig_height = new_fig_width * (total_span_y / total_span_x)
                
                self.truss_canvas.fig.set_size_inches(new_fig_width, new_fig_height, forward=True)
                
        else:
            self.axes.set_aspect('auto') 
            # Reset figure size to default 
            self.truss_canvas.fig.set_size_inches(self.truss_canvas.default_width, 
                                                  self.truss_canvas.default_height, 
                                                  forward=True)

        self.axes.set_title(f"Truss Diagram: {os.path.basename(self.current_data_dir) if self.current_data_dir else 'No Data'}")
        self.axes.set_xlabel("X-coordinate (m)")
        self.axes.set_ylabel("Y-coordinate (m)")
        self.axes.grid(True)
        
        self.truss_canvas.fig.tight_layout()
        self.truss_canvas.draw()
        
    def export_plot(self):
        """Saves the current Matplotlib plot to a PNG file."""
        if self.data is None:
            QMessageBox.warning(self, "Export Error", "No truss data loaded to export.")
            return

        default_filename = os.path.basename(self.current_data_dir) + "_truss.png"
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Truss Diagram",
                                                 default_filename,
                                                 "PNG Files (*.png);;All Files (*)", options=options)
        
        if file_path:
            try:
                self.refresh_plot() 
                self.truss_canvas.fig.savefig(file_path, dpi=300, bbox_inches='tight')
                self.status_label.setText(f"Successfully exported plot to: {file_path}")
            except Exception as e:
                self.status_label.setText(f"Error during export: {str(e)}")
                QMessageBox.critical(self, "Export Error", f"Failed to save file: {str(e)}")
                
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

    window = TrussRenderer()
    
    if is_standalone:
        window.show()
        sys.exit(app.exec())
    
    return window

if __name__ == '__main__':
    main()