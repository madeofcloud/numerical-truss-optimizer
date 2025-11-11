import sys
import os
import numpy as np
import pandas as pd
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                               QHBoxLayout, QLabel, QPushButton, QCheckBox,
                               QLineEdit, QFileDialog, QSlider, QGridLayout,
                               QMessageBox, QFrame, QSizePolicy, QGroupBox)
from PySide6.QtCore import Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.patches as patches

# --- ASSUMED EXTERNAL IMPORTS / PLACEHOLDER FUNCTIONS ---
try:
    from truss_analysis import load_truss_data, run_truss_simulation
except ImportError:
    def load_truss_data(points_path, trusses_path, supports_path, materials_path, loads_path):
        """Mock load function for demonstration."""
        print(f"Attempting to load data from {os.path.dirname(points_path)}")
        for p in [points_path, trusses_path, supports_path, materials_path]:
            if not os.path.exists(p):
                raise FileNotFoundError(p)
        data = {}
        points_df = pd.read_csv(points_path)
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
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)


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
        control_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        control_panel.setFrameShape(QFrame.Shape.StyledPanel)

        # --- Design Selection ---
        design_group = QGroupBox("Design Directory")
        design_layout = QVBoxLayout(design_group)

        path_layout = QHBoxLayout()
        self.path_line_edit = QLineEdit(self.current_data_dir)
        self.path_line_edit.setReadOnly(True)
        path_layout.addWidget(self.path_line_edit)

        select_button = QPushButton("Select...")
        select_button.clicked.connect(self.select_design_directory)
        path_layout.addWidget(select_button)
        design_layout.addLayout(path_layout)
        control_layout.addWidget(design_group)

        # --- Axis Limits & Aspect Ratio ---
        axis_group = QGroupBox("Axis Limits & Aspect")
        axis_layout = QGridLayout(axis_group)
        self.square_aspect_cb = QCheckBox("Force Square Aspect Ratio")
        self.square_aspect_cb.setChecked(True)
        self.square_aspect_cb.stateChanged.connect(self.refresh_plot)
        axis_layout.addWidget(self.square_aspect_cb, 0, 0, 1, 4)
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
        reset_limits_btn = QPushButton("Reset to Auto Limits")
        reset_limits_btn.clicked.connect(self.reset_axis_limits)
        axis_layout.addWidget(reset_limits_btn, 3, 0, 1, 4)
        control_layout.addWidget(axis_group)

        # --- NEW: Labels & Title Group ---
        label_group = QGroupBox("Labels & Title")
        label_layout = QGridLayout(label_group)
        label_layout.addWidget(QLabel("Plot Title:"), 0, 0)
        self.title_edit = QLineEdit()
        self.title_edit.editingFinished.connect(self.refresh_plot)
        label_layout.addWidget(self.title_edit, 0, 1, 1, 2)
        label_layout.addWidget(QLabel("X-Axis Label:"), 1, 0)
        self.xlabel_edit = QLineEdit("X-coordinate (m)")
        self.xlabel_edit.editingFinished.connect(self.refresh_plot)
        label_layout.addWidget(self.xlabel_edit, 1, 1, 1, 2)
        label_layout.addWidget(QLabel("Y-Axis Label:"), 2, 0)
        self.ylabel_edit = QLineEdit("Y-coordinate (m)")
        self.ylabel_edit.editingFinished.connect(self.refresh_plot)
        label_layout.addWidget(self.ylabel_edit, 2, 1, 1, 2)
        label_layout.addWidget(QLabel("Axis/Title Size:"), 3, 0)
        self.axis_text_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.axis_text_size_slider.setRange(8, 20)
        self.axis_text_size_slider.setValue(12)
        self.axis_text_size_slider.valueChanged.connect(self.refresh_plot)
        self.axis_text_size_label = QLabel(f"{self.axis_text_size_slider.value()} pts")
        self.axis_text_size_slider.valueChanged.connect(lambda v, vl=self.axis_text_size_label: vl.setText(f"{v} pts"))
        label_layout.addWidget(self.axis_text_size_slider, 4, 0, 1, 2)
        label_layout.addWidget(self.axis_text_size_label, 4, 2)
        control_layout.addWidget(label_group)
        # ---------------------------------

        # --- Toggles and Scaling ---
        config_group = QGroupBox("Display Options")
        config_layout = QGridLayout(config_group)
        self.show_nodes_cb = QCheckBox("Show Node IDs")
        self.show_nodes_cb.setChecked(True)
        self.show_nodes_cb.stateChanged.connect(self.refresh_plot)
        config_layout.addWidget(self.show_nodes_cb, 1, 0, 1, 3)
        self.show_trusses_cb = QCheckBox("Show Element IDs")
        self.show_trusses_cb.setChecked(False)
        self.show_trusses_cb.stateChanged.connect(self.refresh_plot)
        config_layout.addWidget(self.show_trusses_cb, 2, 0, 1, 3)
        config_layout.addWidget(QLabel("Force Arrow Scale:"), 3, 0)
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(1, 20)
        self.scale_slider.setValue(10)
        self.scale_slider.valueChanged.connect(self.refresh_plot)
        self.scale_label = QLabel(f"{self.scale_slider.value()/100:.2f}")
        self.scale_slider.valueChanged.connect(lambda v, vl=self.scale_label: vl.setText(f"{v/100:.2f}"))
        config_layout.addWidget(self.scale_slider, 4, 0, 1, 2)
        config_layout.addWidget(self.scale_label, 4, 2)
        config_layout.addWidget(QLabel("Node/Elem. Size:"), 5, 0)
        self.text_size_slider = QSlider(Qt.Orientation.Horizontal)
        self.text_size_slider.setRange(5, 15)
        self.text_size_slider.setValue(9)
        self.text_size_slider.valueChanged.connect(self.refresh_plot)
        self.text_size_label = QLabel(f"{self.text_size_slider.value()} pts")
        self.text_size_slider.valueChanged.connect(lambda v, vl=self.text_size_label: vl.setText(f"{v} pts"))
        config_layout.addWidget(self.text_size_slider, 6, 0, 1, 2)
        config_layout.addWidget(self.text_size_label, 6, 2)
        config_layout.addWidget(QLabel("Padding/Zoom:"), 7, 0)
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
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

        legend_frame = QFrame()
        legend_frame.setFrameShape(QFrame.Shape.StyledPanel)
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        def create_symbol_label(symbol, color):
            style = f"""QLabel {{ color: {color}; font-size: 14pt; font-weight: bold; padding-right: 5px; }}"""
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
        legend_layout.addWidget(QLabel(" | <b>Member Forces:</b>"))
        legend_layout.addWidget(QLabel("<span style='color:red;'>Tension</span>"))
        legend_layout.addWidget(QLabel("| <span style='color:blue;'>Compression</span>"))
        legend_layout.addWidget(QLabel("| <b>Loads:</b>"))
        legend_layout.addWidget(QLabel("<span style='color:purple;'>Applied Load</span>"))

        viz_layout.addWidget(legend_frame)
        self.main_layout.addWidget(viz_panel)

    ## Data Handling Methods

    def select_design_directory(self):
        """Opens a directory selector dialog and loads the selected data."""
        dialog = QFileDialog(self)
        dialog.setFileMode(QFileDialog.FileMode.Directory)
        if dialog.exec():
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

            points_df = self.data['points']
            if not points_df.empty and 'x' in points_df.columns and 'y' in points_df.columns:
                self.auto_xlim = (points_df['x'].min(), points_df['x'].max())
                self.auto_ylim = (points_df['y'].min(), points_df['y'].max())
                self.reset_axis_limits() # This also triggers a refresh_plot
            
            # UPDATE: Set the default title in the text field
            default_title = f"Truss Diagram: {os.path.basename(self.current_data_dir)}"
            self.title_edit.setText(default_title)

            self.status_label.setText(f"Loaded design: {os.path.basename(self.current_data_dir)}")
            self.export_button.setEnabled(True)
            self.refresh_plot()

        except FileNotFoundError as e:
            msg = f"File not found: {os.path.basename(str(e))}"
            self.status_label.setText(f"Error: {msg}")
            QMessageBox.warning(self, "Error", f"{msg}. Please ensure all required CSV files are in the selected folder.")
            self.data = None
            self.export_button.setEnabled(False)
        except Exception as e:
            self.status_label.setText(f"An unexpected error occurred: {str(e)}")
            self.data = None
            self.export_button.setEnabled(False)

    def reset_axis_limits(self):
        """Resets the axis limit input fields and refreshes the plot."""
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

    def get_user_limits(self):
        """Reads user-defined limits, falling back to auto limits."""
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
        """Draws the truss diagram with all current display settings."""
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
        is_node_indexed = points_df.index.name == 'Node'

        def get_node_coords(node_id):
            try:
                if is_node_indexed:
                    coords = points_df.loc[node_id, ['x', 'y']].values
                elif 'Node' in points_df.columns:
                    coords = points_df[points_df['Node'] == node_id][['x', 'y']].values[0]
                else:
                    coords = points_df.iloc[node_id][['x', 'y']].values
                return coords.flatten()
            except (KeyError, IndexError):
                return None

        stresses_df, _ = run_truss_simulation(data)
        text_size = self.text_size_slider.value()

        # Plot members
        for _, row in trusses_df.iterrows():
            p1 = get_node_coords(row['start'])
            p2 = get_node_coords(row['end'])
            if p1 is None or p2 is None: continue
            
            force_row = stresses_df[stresses_df['element'] == row['element']]
            force = force_row['axial_force'].iloc[0] if not force_row.empty else 0
            color = 'blue' if force < 0 else 'red'
            self.axes.plot([p1[0], p2[0]], [p1[1], p2[1]], color=color, linewidth=2)
            
            if self.show_trusses_cb.isChecked():
                mid_x, mid_y = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2
                self.axes.text(mid_x, mid_y, str(int(row['element'])), ha='center', va='center', fontsize=text_size-2,
                               bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))

        # Plot nodes
        self.axes.plot(points_df['x'], points_df['y'], 'o', color='black', zorder=5, markersize=5)
        if self.show_nodes_cb.isChecked():
            span_x, span_y = self.auto_xlim[1] - self.auto_xlim[0], self.auto_ylim[1] - self.auto_ylim[0]
            max_span = max(span_x, span_y)
            offset = max_span * 0.015 if max_span > 0 else 0.05
            for index, row in points_df.iterrows():
                node_id = index if is_node_indexed else row.get('Node', index)
                if pd.isna(row['x']) or pd.isna(row['y']): continue
                self.axes.text(row['x'] + offset, row['y'] + offset, str(int(node_id)),
                               ha='left', va='bottom', fontsize=text_size, fontweight='bold', zorder=8)

        # Plot supports
        for _, row in supports_df.iterrows():
            node_pos = get_node_coords(row['Node'])
            if node_pos is None: continue
            self.axes.plot(node_pos[0], node_pos[1], 's', color='green', markersize=12, zorder=6)

        # Plot loads
        if data.get('loads') is not None and not data['loads'].empty:
            max_span = max(self.auto_xlim[1] - self.auto_xlim[0], self.auto_ylim[1] - self.auto_ylim[0])
            if max_span <= 0: max_span = 1.0
            arrow_scale = max_span * (self.scale_slider.value() / 100.0)
            for _, row in data['loads'].iterrows():
                node_pos = get_node_coords(row['Node'])
                if node_pos is None: continue
                fx, fy = row.get('Fx', 0), row.get('Fy', 0)
                force_mag = np.sqrt(fx**2 + fy**2)
                if force_mag > 0:
                    unit_fx, unit_fy = fx / force_mag, fy / force_mag
                    dx, dy = unit_fx * arrow_scale, unit_fy * arrow_scale
                    self.axes.arrow(node_pos[0], node_pos[1], dx, dy,
                                    head_width=0.05 * arrow_scale, head_length=0.075 * arrow_scale,
                                    fc='purple', ec='purple', linewidth=2, zorder=7)

        # Apply Axis Limits, Zoom, and Aspect
        (min_x, max_x), (min_y, max_y) = self.get_user_limits()
        span_x, span_y = max_x - min_x, max_y - min_y
        padding = self.zoom_slider.value() / 100.0
        pad_x = span_x * padding / 2 if span_x > 0 else 0.5 * padding
        pad_y = span_y * padding / 2 if span_y > 0 else 0.5 * padding
        self.axes.set_xlim(min_x - pad_x, max_x + pad_x)
        self.axes.set_ylim(min_y - pad_y, max_y + pad_y)

        if self.square_aspect_cb.isChecked():
            self.axes.set_aspect('equal', 'box')
            total_span_x = (max_x + pad_x) - (min_x - pad_x)
            total_span_y = (max_y + pad_y) - (min_y - pad_y)
            if total_span_x > 0 and total_span_y > 0:
                fig_width = self.truss_canvas.default_width
                fig_height = fig_width * (total_span_y / total_span_x)
                self.truss_canvas.fig.set_size_inches(fig_width, fig_height, forward=True)
                # BUG FIX: Notify the layout that the widget's size has changed
                self.truss_canvas.updateGeometry()
        else:
            self.axes.set_aspect('auto')
            self.truss_canvas.fig.set_size_inches(self.truss_canvas.default_width,
                                                  self.truss_canvas.default_height,
                                                  forward=True)
            # BUG FIX: Notify the layout that the widget's size has changed
            self.truss_canvas.updateGeometry()

        # UPDATE: Apply custom labels and font sizes
        axis_fontsize = self.axis_text_size_slider.value()
        title_text = self.title_edit.text()
        if not title_text: # Provide a default if empty
            title_text = f"Truss Diagram: {os.path.basename(self.current_data_dir) if self.current_data_dir else 'No Data'}"
            
        self.axes.set_title(title_text, fontsize=axis_fontsize)
        self.axes.set_xlabel(self.xlabel_edit.text(), fontsize=axis_fontsize)
        self.axes.set_ylabel(self.ylabel_edit.text(), fontsize=axis_fontsize)
        self.axes.grid(True)
        self.truss_canvas.fig.tight_layout()
        self.truss_canvas.draw()

    def export_plot(self):
        """Saves the current Matplotlib plot to a PNG file."""
        if self.data is None:
            QMessageBox.warning(self, "Export Error", "No truss data loaded to export.")
            return

        default_filename = os.path.basename(self.current_data_dir) + "_truss.png"
        file_path, _ = QFileDialog.getSaveFileName(self, "Save Truss Diagram",
                                                     default_filename,
                                                     "PNG Files (*.png);;All Files (*)")
        if file_path:
            try:
                self.refresh_plot()
                self.truss_canvas.fig.savefig(file_path, dpi=300, bbox_inches='tight')
                self.status_label.setText(f"Successfully exported plot to: {file_path}")
            except Exception as e:
                self.status_label.setText(f"Error during export: {str(e)}")
                QMessageBox.critical(self, "Export Error", f"Failed to save file: {str(e)}")

    def closeEvent(self, event):
        self.deleteLater()
        event.accept()

def main():
    """Stand-alone execution entry point."""
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