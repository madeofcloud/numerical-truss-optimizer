#!/usr/bin/env python3
"""
Truss Editor / Creator

A single-file PyQt5 application that lets users:
 - interactively place, move, and delete nodes (points)
 - draw truss elements by dragging between nodes
 - switch between datasets (points, trusses, supports, materials, loads) with an editable table
 - export the design as a folder of CSV files
 - visualize axial forces (via a plug-in run_truss_simulation) and loads

Dependencies: PyQt5, matplotlib, pandas, numpy, PyQt5.QtSvg (NEW)
Run: python truss_editor.py

This file builds on the visualization implementation you provided and extends it into an
interactive editor with a sidebar table editor and export functionality.

--- UPDATES IMPLEMENTED ---
1. Replaced tool dropdown with a QToolBar with toggle buttons using hardcoded SVG icons.
2. Increased the window size and the width of the left control panel.
3. Connected the PandasModel data change signal to redraw the truss visualization.
4. **FIX:** Added missing `QActionGroup` import.
5. **NEW:** Updated icon generation using `PyQt5.QtSvg.QSvgRenderer` for cleaner icons.
6. **CONFIRMED:** Redraw is triggered automatically on table value update (including keyboard entry).
"""

import sys
import os
import math
import tempfile
import numpy as np
import pandas as pd
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QPushButton, QCheckBox, QLineEdit, QFileDialog, QSlider,
                             QGridLayout, QMessageBox, QFrame, QSizePolicy, QGroupBox,
                             QComboBox, QStackedWidget, QTableView, QAbstractItemView,
                             QToolBar, QAction, QInputDialog, QActionGroup) # <-- QActionGroup added
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QVariant, pyqtSignal, QSize, QByteArray # <-- QByteArray added
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PyQt5.QtSvg import QSvgRenderer # <-- QtSvg dependency added
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

# --- Placeholder simulation functions (replace with your real functions) ---
try:
    from truss_analysis import run_truss_simulation
except Exception:
    def run_truss_simulation(data):
        # produce a simple axial_force column for demo
        t = data['trusses'].copy()
        if 'element' in t.columns:
            # Check if there are elements before trying to assign forces
            if not t.empty:
                t['axial_force'] = np.where(np.arange(len(t)) % 2 == 0, 1000.0, -800.0)
            else:
                t['axial_force'] = []
        else:
            t['axial_force'] = 0.0
        return t, None
# ---------------------------------------------------------------------------

# --- Icon Generation Helper (Updated to use QtSvg) ---
def create_svg_icon(svg_content, size=32):
    """Creates a QIcon from an SVG string using QSvgRenderer."""
    svg_data = f"""<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">
    {svg_content}
    </svg>"""
    
    # Render SVG using QtSvg
    renderer = QSvgRenderer(QByteArray(svg_data.encode('utf-8')))
    
    if not renderer.isValid():
        # Fallback to a blank icon if rendering fails
        return QIcon()

    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    
    return QIcon(pixmap)


def get_icon(tool_name):
    """Generates simple QIcons for the tools using SVG."""
    size = 32
    
    # Define simple SVG content for visualization
    if tool_name == 'select':
        # Simple arrow pointer
        svg = f'<polygon points="4,4 4,{size-4} {size-8},{size/2}" fill="black"/>'

    elif tool_name == 'add_node':
        # Plus in a circle
        svg = f'<circle cx="{size/2}" cy="{size/2}" r="{size/2.5}" fill="none" stroke="black" stroke-width="2"/>'
        svg += f'<line x1="{size/2}" y1="{size/4}" x2="{size/2}" y2="{size*3/4}" stroke="black" stroke-width="2"/>'
        svg += f'<line x1="{size/4}" y1="{size/2}" x2="{size*3/4}" y2="{size/2}" stroke="black" stroke-width="2"/>'
        
    elif tool_name == 'connect':
        # Line between two dots
        svg = f'<circle cx="{size/4}" cy="{size/2}" r="4" fill="black"/>'
        svg += f'<circle cx="{size*3/4}" cy="{size/2}" r="4" fill="black"/>'
        svg += f'<line x1="{size/4}" y1="{size/2}" x2="{size*3/4}" y2="{size/2}" stroke="black" stroke-width="3"/>'
        
    elif tool_name == 'move':
        # Four-directional arrow cross
        svg = f'<path d="M{size/2},4 L{size-4},{size/2} L{size/2},{size-4} L4,{size/2} L{size/2},4" fill="#ffaa00" stroke="black" stroke-width="1"/>'
        svg += f'<circle cx="{size/2}" cy="{size/2}" r="3" fill="black"/>'

    elif tool_name == 'delete':
        # 'X' (Delete)
        svg = f'<line x1="8" y1="8" x2="{size-8}" y2="{size-8}" stroke="red" stroke-width="3"/>'
        svg += f'<line x1="8" y1="{size-8}" x2="{size-8}" y2="8" stroke="red" stroke-width="3"/>'
    else:
        return QIcon() # Fallback

    return create_svg_icon(svg, size)
# --------------------------------


class PandasModel(QAbstractTableModel):
    """A minimal editable QAbstractTableModel wrapping a pandas DataFrame."""
    dataChangedSignal = pyqtSignal()

    def __init__(self, df=pd.DataFrame(), parent=None):
        super().__init__(parent)
        self._df = df.copy()

    def rowCount(self, parent=QModelIndex()):
        return len(self._df.index)

    def columnCount(self, parent=QModelIndex()):
        return len(self._df.columns)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return QVariant()
        r, c = index.row(), index.column()
        val = self._df.iloc[r, c]
        if role == Qt.DisplayRole or role == Qt.EditRole:
            return str(val) if not pd.isna(val) else ""
        return QVariant()

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role != Qt.DisplayRole:
            return QVariant()
        if orientation == Qt.Horizontal:
            return str(self._df.columns[section])
        else:
            return str(self._df.index[section])

    def flags(self, index):
        if not index.isValid():
            return Qt.ItemIsEnabled
        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            r, c = index.row(), index.column()
            col = self._df.columns[c]
            
            # --- Robustness check for redrawing: only allow numeric/valid values for 'x'/'y' etc. ---
            try:
                if self._df.columns[c] in ['x', 'y', 'Fx', 'Fy', 'E', 'A', 'Node', 'start', 'end', 'element']:
                    if pd.api.types.is_integer_dtype(self._df[col].dtype) or self._df.columns[c] in ['Node', 'start', 'end', 'element']:
                        new_value = int(value)
                    elif pd.api.types.is_float_dtype(self._df[col].dtype):
                        new_value = float(value)
                    else:
                        new_value = value
                else:
                    new_value = value
            except Exception:
                # If conversion fails for a numeric column, reject the edit or revert.
                if self._df.columns[c] in ['x', 'y', 'Fx', 'Fy', 'E', 'A', 'Node', 'start', 'end', 'element']:
                    QMessageBox.warning(self.parent(), "Input Error", 
                                        f"Value must be a valid number for column '{col}'. Edit rejected.")
                    return False
                new_value = value # Fallback to string if not critical
            # --- End Robustness Check ---
            
            self._df.iloc[r, c] = new_value
            self.dataChanged.emit(index, index, [Qt.DisplayRole])
            self.dataChangedSignal.emit() # Signal for the editor to redraw on edit completion
            return True
        return False

    def set_dataframe(self, df):
        self.beginResetModel()
        self._df = df.copy()
        self.endResetModel()
        self.dataChangedSignal.emit()

    def dataframe(self):
        return self._df.copy()

    def insert_row(self, values=None):
        values = values or {}
        self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
        new_row = {c: values.get(c, np.nan) for c in self._df.columns}
        self._df = pd.concat([self._df, pd.DataFrame([new_row])], ignore_index=True)
        self.endInsertRows()
        self.dataChangedSignal.emit()

    def remove_row(self, row_idx):
        if 0 <= row_idx < self.rowCount():
            self.beginRemoveRows(QModelIndex(), row_idx, row_idx)
            self._df = self._df.drop(self._df.index[row_idx]).reset_index(drop=True)
            self.endRemoveRows()
            self.dataChangedSignal.emit()


class MplCanvas(FigureCanvas):
    def __init__(self, parent=None, width=6, height=5, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        super().__init__(self.fig)
        self.setParent(parent)
        self.axes = self.fig.add_subplot(111)
        self.default_width = width
        self.default_height = height


class TrussEditor(QMainWindow):
    # Tool names and corresponding internal keys
    TOOLS = {'Select': 'select', 'Add Node': 'add_node', 'Connect': 'connect', 'Move': 'move', 'Delete': 'delete'}

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Truss Creator & Editor")
        # 1. Increased window size
        self.resize(1400, 900)

        # Dataframes (default blank structures)
        self.points = pd.DataFrame(columns=['Node', 'x', 'y'])
        self.trusses = pd.DataFrame(columns=['element', 'start', 'end'])
        self.supports = pd.DataFrame(columns=['Node', 'type'])
        self.materials = pd.DataFrame(columns=['material', 'E', 'A'])
        self.loads = pd.DataFrame(columns=['Node', 'Fx', 'Fy'])

        # keep internal indices for automatic IDs
        self._next_node_id = 1
        self._next_element_id = 1

        self.current_tool = 'select'  # 'add_node', 'connect', 'move', 'delete'
        self.dragging_node = None
        self.connect_start_node = None

        self.current_data_dir = ''

        self.init_ui()
        self.redraw()

    def init_ui(self):
        central = QWidget()
        central_layout = QHBoxLayout(central)
        self.setCentralWidget(central)

        # Left: Tools & dataset switcher & table editor
        left_panel = QFrame()
        # 2. Increased left panel width
        left_panel.setFixedWidth(450)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignTop)

        # --- Tools QToolBar (Replacing dropdown) ---
        tool_label = QLabel("<b>Editor Tools</b>")
        left_layout.addWidget(tool_label)
        
        self.tool_bar = QToolBar("Tools")
        self.tool_bar.setMovable(False)
        self.tool_bar.setIconSize(QSize(32, 32))
        self.tool_actions = {}
        self.tool_group = QActionGroup(self.tool_bar)
        self.tool_group.setExclusive(True)

        for name, key in self.TOOLS.items():
            action = QAction(name, self.tool_bar)
            action.setIcon(get_icon(key)) # Use SVG icon
            action.setCheckable(True)
            action.setActionGroup(self.tool_group)
            action.triggered.connect(lambda checked, k=key: self.tool_changed(k))
            self.tool_bar.addAction(action)
            self.tool_actions[key] = action

        # Set 'select' as default checked tool
        self.tool_actions['select'].setChecked(True)
        left_layout.addWidget(self.tool_bar)

        clear_btn = QPushButton("Clear All")
        clear_btn.clicked.connect(self.clear_all)
        left_layout.addWidget(clear_btn)
        
        left_layout.addSpacing(10)
        # ------------------------------------------

        # Dataset switcher
        dataset_label = QLabel("<b>Editing Dataset</b>")
        left_layout.addWidget(dataset_label)
        self.dataset_combo = QComboBox()
        self.dataset_combo.addItems(['points', 'trusses', 'supports', 'materials', 'loads'])
        self.dataset_combo.currentTextChanged.connect(self.dataset_changed)
        left_layout.addWidget(self.dataset_combo)

        # Table view / editor
        self.table_view = QTableView()
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_view.doubleClicked.connect(self.table_double_clicked)
        self.table_view.setColumnWidth(0, 80) # Widen columns
        self.table_view.setColumnWidth(1, 80)
        left_layout.addWidget(self.table_view, stretch=1)

        # Table controls
        tbl_controls = QHBoxLayout()
        add_row_btn = QPushButton("Add Row")
        add_row_btn.clicked.connect(self.add_row)
        del_row_btn = QPushButton("Delete Row")
        del_row_btn.clicked.connect(self.delete_row)
        tbl_controls.addWidget(add_row_btn)
        tbl_controls.addWidget(del_row_btn)
        left_layout.addLayout(tbl_controls)

        # Export / load
        export_btn = QPushButton("Export Design (CSV folder)")
        export_btn.clicked.connect(self.export_design)
        load_btn = QPushButton("Load Design (folder)")
        load_btn.clicked.connect(self.load_design)
        left_layout.addWidget(export_btn)
        left_layout.addWidget(load_btn)

        # small instructions
        instr = QLabel("Click on canvas to add nodes; drag between nodes to connect when 'Connect' tool is active.\nUse 'Move' to drag nodes. Table edits update the view automatically.")
        instr.setWordWrap(True)
        left_layout.addWidget(instr)

        central_layout.addWidget(left_panel)

        # Right: canvas & controls
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Canvas
        self.canvas = MplCanvas(self, width=8, height=6, dpi=100)
        self.canvas.mpl_connect('button_press_event', self.on_canvas_click)
        self.canvas.mpl_connect('motion_notify_event', self.on_canvas_motion)
        self.canvas.mpl_connect('button_release_event', self.on_canvas_release)
        right_layout.addWidget(self.canvas, stretch=1)

        # Visualization controls
        vis_controls = QHBoxLayout()
        self.show_nodes_cb = QCheckBox("Show Node IDs")
        self.show_nodes_cb.setChecked(True)
        self.show_nodes_cb.stateChanged.connect(self.redraw)
        self.show_trusses_cb = QCheckBox("Show Truss IDs")
        self.show_trusses_cb.setChecked(False)
        self.show_trusses_cb.stateChanged.connect(self.redraw)
        vis_controls.addWidget(self.show_nodes_cb)
        vis_controls.addWidget(self.show_trusses_cb)

        compute_btn = QPushButton("Run Simulation (Show Force)")
        compute_btn.clicked.connect(self.run_simulation_and_show)
        vis_controls.addWidget(compute_btn)

        right_layout.addLayout(vis_controls)

        central_layout.addWidget(right_panel, stretch=1)

        # Table model initialization
        self.current_model = PandasModel(self.points, parent=self)
        self.table_view.setModel(self.current_model)
        # Connect model change signal to redraw (Handles keyboard edits, drag/drop etc.)
        self.current_model.dataChangedSignal.connect(self.redraw_safe)

    # ---------- Data operations ----------
    def ensure_points_index(self):
        if 'Node' not in self.points.columns:
            # Handle case where Node column might be missing, although it's added on load/export
            self.points.insert(0, 'Node', np.arange(1, len(self.points) + 1))
            self._next_node_id = int(self.points['Node'].max() + 1)
        # Also ensure points data frame is updated if the active model is points
        if self.dataset_combo.currentText() == 'points':
            self.points = self.current_model.dataframe()


    def add_point(self, x, y):
        node_id = self._next_node_id
        self._next_node_id += 1
        new_row = {'Node': node_id, 'x': float(x), 'y': float(y)}
        self.points = pd.concat([self.points, pd.DataFrame([new_row])], ignore_index=True)
        self.current_model.set_dataframe(self.points)
        return node_id

    def delete_node(self, node_id):
        # remove node and any trusses/supports/loads referencing it
        self.points = self.points[self.points['Node'] != node_id].reset_index(drop=True)
        self.trusses = self.trusses[(self.trusses['start'] != node_id) & (self.trusses['end'] != node_id)].reset_index(drop=True)
        self.supports = self.supports[self.supports['Node'] != node_id].reset_index(drop=True)
        self.loads = self.loads[self.loads['Node'] != node_id].reset_index(drop=True)
        # Update current model only if it was affected
        dfname = self.dataset_combo.currentText()
        if dfname == 'points':
            self.current_model.set_dataframe(self.points)
        elif dfname == 'trusses':
            self.current_model.set_dataframe(self.trusses)
        elif dfname == 'supports':
            self.current_model.set_dataframe(self.supports)
        elif dfname == 'loads':
            self.current_model.set_dataframe(self.loads)

    def add_truss(self, start, end):
        # Prevent self-loop or duplicate connection (direction doesn't matter)
        if start == end:
            return
        
        # Check for existing truss between start and end (either direction)
        existing1 = self.trusses[(self.trusses['start'] == start) & (self.trusses['end'] == end)]
        existing2 = self.trusses[(self.trusses['start'] == end) & (self.trusses['end'] == start)]
        if not existing1.empty or not existing2.empty:
            QMessageBox.information(self, "Truss Connect", "Truss already exists between these nodes.")
            return

        element = self._next_element_id
        self._next_element_id += 1
        row = {'element': int(element), 'start': int(start), 'end': int(end)}
        self.trusses = pd.concat([self.trusses, pd.DataFrame([row])], ignore_index=True)
        if self.dataset_combo.currentText() == 'trusses':
            self.current_model.set_dataframe(self.trusses)

    # ---------- UI handlers ----------
    def tool_changed(self, tool_key):
        self.current_tool = tool_key
        # Ensure only the new tool's action is checked
        if not self.tool_actions[tool_key].isChecked():
            self.tool_actions[tool_key].setChecked(True)
        
        # Clear connect state if switching away from 'connect'
        if self.current_tool != 'connect':
            self.connect_start_node = None
        
        # Clear dragging state if switching away from 'move'
        if self.current_tool != 'move':
            self.dragging_node = None
            
        self.redraw() # Redraw for visual feedback if needed (e.g., clearing connect start node highlight)

    def dataset_changed(self, text):
        # swap model to chosen dataframe
        df_map = {
            'points': self.points,
            'trusses': self.trusses,
            'supports': self.supports,
            'materials': self.materials,
            'loads': self.loads
        }
        
        df_to_set = df_map.get(text, pd.DataFrame())
        
        # Sanity check for points index on switch
        if text == 'points' and 'Node' not in df_to_set.columns and not df_to_set.empty:
            df_to_set.insert(0, 'Node', np.arange(1, len(df_to_set) + 1))
            self.points = df_to_set # Update internal points DF
            
        self.current_model.set_dataframe(df_to_set)
        self.redraw() # Redraw to ensure consistency

    def add_row(self):
        dfname = self.dataset_combo.currentText()
        model = self.current_model
        
        # Pre-populate some IDs/defaults if applicable
        values = {}
        if dfname == 'points' and 'Node' in model.dataframe().columns:
            values['Node'] = self._next_node_id
            self._next_node_id += 1
        elif dfname == 'trusses' and 'element' in model.dataframe().columns:
            values['element'] = self._next_element_id
            self._next_element_id += 1
        elif dfname == 'supports':
            values['type'] = 'pin'
        elif dfname == 'materials':
            values['material'] = f'mat{len(model.dataframe()) + 1}'

        model.insert_row(values=values)
        
        # write back immediately
        self._sync_dataframe(dfname, model.dataframe())
        # redraw is triggered by model.dataChangedSignal

    def delete_row(self):
        idxs = self.table_view.selectionModel().selectedRows()
        if not idxs:
            QMessageBox.information(self, "Delete Row", "Please select a row to delete.")
            return
        
        row = idxs[0].row()
        dfname = self.dataset_combo.currentText()
        df_before = self.current_model.dataframe()
        
        # Get the Node/element ID to be deleted for better integrity checking
        if dfname == 'points' and 'Node' in df_before.columns:
            deleted_id = df_before.iloc[row]['Node']
            # Special handling for node deletion to clean up other DFs
            self.delete_node(deleted_id)
            # delete_node handles updating the model if it's the points table, 
            # and triggers redraw via set_dataframe.
            return
        
        # Normal row deletion
        self.current_model.remove_row(row)
        
        # write back
        self._sync_dataframe(dfname, self.current_model.dataframe())
        # redraw is triggered by model.dataChangedSignal

    def _sync_dataframe(self, dfname, df):
        """Helper to sync the internal dataframes."""
        if dfname == 'points':
            self.points = df
        elif dfname == 'trusses':
            self.trusses = df
        elif dfname == 'supports':
            self.supports = df
        elif dfname == 'materials':
            self.materials = df
        elif dfname == 'loads':
            self.loads = df

    def table_double_clicked(self, idx):
        # convenience: switch to select tool when double-clicking
        if self.current_tool != 'select':
            self.tool_actions['select'].setChecked(True)
            self.tool_changed('select')
        
    # ---------- Canvas interactions ----------
    def get_node_at(self, x, y, tol=0.05):
        # find nearest node within tolerance in data units (approx)
        if self.points.empty or 'Node' not in self.points.columns:
            return None
        
        # Calculate tolerance based on current view limits (zoom factor)
        xfact = self.zoom_factor()
        tol = 0.05 * max(1.0, xfact)

        dists = np.hypot(self.points['x'] - x, self.points['y'] - y)
        min_idx_loc = dists.idxmin() if not dists.empty else None
        
        if min_idx_loc is None:
            return None
            
        if dists.loc[min_idx_loc] <= tol:
            # return Node ID
            return int(self.points.loc[min_idx_loc, 'Node'])
        return None

    def on_canvas_click(self, event):
        if event.xdata is None or event.ydata is None or event.button != 1: # Only handle left-click
            return
        x, y = float(event.xdata), float(event.ydata)

        if self.current_tool == 'add_node':
            nid = self.add_point(x, y)
            self.dataset_combo.setCurrentText('points')
            self.redraw()
            return

        # detect clicked node
        node_id = self.get_node_at(x, y)

        if self.current_tool == 'connect':
            if node_id is None:
                return
            if self.connect_start_node is None:
                self.connect_start_node = node_id
            else:
                if node_id != self.connect_start_node:
                    self.add_truss(self.connect_start_node, node_id)
                    self.dataset_combo.setCurrentText('trusses')
                self.connect_start_node = None
            self.redraw()
            return

        if self.current_tool == 'move':
            if node_id is not None:
                self.dragging_node = node_id
            return

        if self.current_tool == 'delete':
            if node_id is not None:
                self.delete_node(node_id)
                self.redraw()
            else:
                # try to delete truss if click near member center
                clicked_truss_index = self.find_truss_near(x, y)
                if clicked_truss_index is not None:
                    self.trusses = self.trusses.drop(clicked_truss_index).reset_index(drop=True)
                    # Update model if 'trusses' is the active dataset
                    if self.dataset_combo.currentText() == 'trusses':
                        self.current_model.set_dataframe(self.trusses)
                    self.redraw()
            return

    def on_canvas_motion(self, event):
        if event.xdata is None or event.ydata is None:
            return
        x, y = float(event.xdata), float(event.ydata)
        if self.current_tool == 'move' and self.dragging_node is not None:
            # update node coordinates
            idx = self.points.index[self.points['Node'] == self.dragging_node]
            if len(idx) > 0:
                i = idx[0]
                self.points.at[i, 'x'] = x
                self.points.at[i, 'y'] = y
                # Update model and redraw if 'points' is active dataset
                if self.dataset_combo.currentText() == 'points':
                    # Need to manually update the model's DF to show change in table immediately
                    self.current_model._df.loc[i, 'x'] = x
                    self.current_model._df.loc[i, 'y'] = y
                    # Emit dataChanged for the two cells
                    idx_x = self.current_model.index(i, self.current_model._df.columns.get_loc('x'))
                    idx_y = self.current_model.index(i, self.current_model._df.columns.get_loc('y'))
                    self.current_model.dataChanged.emit(idx_x, idx_x, [Qt.DisplayRole])
                    self.current_model.dataChanged.emit(idx_y, idx_y, [Qt.DisplayRole])
                
                self.redraw()

    def on_canvas_release(self, event):
        if self.current_tool == 'move' and self.dragging_node is not None:
            self.dragging_node = None
            # Ensure the table is fully synced after drag if 'points' is not the active table
            if self.dataset_combo.currentText() != 'points':
                 # If points was modified by motion, ensure internal model is synced
                if 'Node' in self.points.columns:
                    self.points = self.points.sort_values(by='Node').reset_index(drop=True)

    def find_truss_near(self, x, y, tol=0.05):
        # simple distance from point to segment
        xfact = self.zoom_factor()
        tol = 0.05 * max(1.0, xfact)
        
        for i, row in self.trusses.iterrows():
            p1 = self.node_coords(row.get('start'))
            p2 = self.node_coords(row.get('end'))
            if p1 is None or p2 is None:
                continue
            d = self.point_to_segment_distance((x, y), p1, p2)
            if d <= tol:
                return i # Return index of the truss in the dataframe
        return None

    def point_to_segment_distance(self, p, a, b):
        # p, a, b are (x,y)
        px, py = p
        ax, ay = a
        bx, by = b
        dx, dy = bx - ax, by - ay
        if dx == 0 and dy == 0:
            return math.hypot(px - ax, py - ay)
        
        # Project point onto line (t is the parameter along the segment)
        t = ((px - ax) * dx + (py - ay) * dy) / (dx*dx + dy*dy)
        t = max(0.0, min(1.0, t)) # Clamp t to 0..1 to find closest point on segment
        
        projx, projy = ax + t * dx, ay + t * dy
        return math.hypot(px - projx, py - projy)

    def node_coords(self, node_id):
        # Ensure 'Node' column is present for lookup
        if 'Node' not in self.points.columns or self.points.empty:
            return None

        # Ensure node_id is convertible to the type in the column (e.g., int)
        try:
            node_id = int(node_id)
        except ValueError:
            return None

        r = self.points[self.points['Node'] == node_id]
        if r.empty:
            return None
        # Use iloc[0] to access the data without index issues
        row = r.iloc[0]
        # Basic check for existence of 'x' and 'y'
        if 'x' in row and 'y' in row:
             return float(row['x']), float(row['y'])
        return None


    def zoom_factor(self):
        # heuristic for tolerance scaling
        ax = self.canvas.axes
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        x_range = xlim[1] - xlim[0]
        y_range = ylim[1] - ylim[0]
        if x_range == 0 or y_range == 0:
            return 1.0
        return max(x_range, y_range)

    # ---------- Drawing ----------
    def redraw_safe(self):
        """Wrapper to catch errors during redraw due to invalid table data."""
        try:
            # Sync the internal DF before drawing, as PandasModel.setData only updates _df
            dfname = self.dataset_combo.currentText()
            self._sync_dataframe(dfname, self.current_model.dataframe())
            self.redraw()
        except Exception as e:
            # We silently fail the redraw and rely on model validation to reject bad user input.
            pass


    def redraw(self):
        ax = self.canvas.axes
        ax.cla()
        ax.set_aspect('equal', adjustable='box')

        # draw trusses
        for _, row in self.trusses.iterrows():
            a = self.node_coords(row.get('start'))
            b = self.node_coords(row.get('end'))
            if a is None or b is None:
                continue
            
            color = 'gray'
            # Highlight the element being connected if the tool is 'connect' and it's the start node
            if self.current_tool == 'connect' and row.get('start') == self.connect_start_node:
                color = '#ffaa00' # Orange highlight
                
            ax.plot([a[0], b[0]], [a[1], b[1]], '-', linewidth=2, color=color, zorder=1)
            if self.show_trusses_cb.isChecked() and 'element' in row:
                try:
                    mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
                    ax.text(mx, my, str(int(row['element'])), ha='center', va='center', fontsize=8, bbox=dict(facecolor='white', alpha=0.6), zorder=4)
                except ValueError:
                    pass # Skip if element ID is invalid

        # draw nodes
        if not self.points.empty and 'x' in self.points.columns and 'y' in self.points.columns:
            # Check for invalid data before plotting
            valid_points = self.points.dropna(subset=['x', 'y'])
            if not valid_points.empty:
                ax.plot(valid_points['x'], valid_points['y'], 'o', markersize=6, color='black', zorder=5)
            
            if self.show_nodes_cb.isChecked() and 'Node' in self.points.columns and self.points['Node'].notnull().all():
                for _, row in valid_points.iterrows():
                    try:
                        ax.text(row['x'] + 0.02, row['y'] + 0.02, str(int(row['Node'])), fontsize=9, zorder=6)
                    except ValueError:
                        pass # Skip if Node ID is invalid

        # draws supports
        for _, row in self.supports.iterrows():
            pos = self.node_coords(row.get('Node'))
            if pos is None:
                continue
            ax.plot(pos[0], pos[1], 's', color='green', markersize=10, zorder=3)

        # draws loads as arrows
        if not self.loads.empty:
            for _, row in self.loads.iterrows():
                pos = self.node_coords(row.get('Node'))
                if pos is None:
                    continue
                try:
                    fx = float(row.get('Fx', 0.0) or 0.0)
                    fy = float(row.get('Fy', 0.0) or 0.0)
                except ValueError:
                    continue # Skip if force values are invalid

                mag = math.hypot(fx, fy)
                if mag == 0:
                    continue
                ux, uy = fx / mag, fy / mag
                scale = 0.2 * max(0.2, self.zoom_factor() / 10.0) # Adaptive scale
                
                # Use ax.quiver for better arrow drawing if needed, but ax.arrow is simpler.
                ax.arrow(pos[0], pos[1], ux*scale, uy*scale, head_width=0.08*scale, head_length=0.12*scale, fc='purple', ec='purple', zorder=2)

        ax.set_title('Truss Editor', fontsize=14)
        ax.set_xlabel('X Coordinate')
        ax.set_ylabel('Y Coordinate')
        ax.grid(True)
        self.canvas.fig.tight_layout()
        self.canvas.draw()

    def run_simulation_and_show(self):
        data = {
            'points': self.points.copy(),
            'trusses': self.trusses.copy(),
            'supports': self.supports.copy(),
            'materials': self.materials.copy(),
            'loads': self.loads.copy()
        }
        try:
            stresses, aux = run_truss_simulation(data)
            
            ax = self.canvas.axes
            ax.cla() # Clear for force visualization overlay
            ax.set_aspect('equal', adjustable='box')
            
            # Find max absolute force for normalization
            if 'axial_force' in stresses.columns and not stresses['axial_force'].empty:
                max_abs_force = stresses['axial_force'].abs().max()
                max_abs_force = max(max_abs_force, 1.0) # Avoid division by zero
            else:
                max_abs_force = 1.0

            # Draw trusses with color/thickness based on force
            for _, row in self.trusses.iterrows():
                a = self.node_coords(row.get('start'))
                b = self.node_coords(row.get('end'))
                if a is None or b is None:
                    continue
                
                frow = stresses[stresses['element'] == row['element']]
                
                f = 0.0
                if not frow.empty and 'axial_force' in stresses.columns:
                    try:
                        f = float(frow['axial_force'].iloc[0])
                    except ValueError:
                        pass # Use 0.0 if value is not numeric

                if f > 0: # Tension
                    color = 'blue'
                elif f < 0: # Compression
                    color = 'red'
                else:
                    color = 'gray'
                
                # Scale thickness based on force magnitude (max 5)
                thickness = 2 + 3 * (abs(f) / max_abs_force)
                ax.plot([a[0], b[0]], [a[1], b[1]], '-', linewidth=thickness, color=color, zorder=1)
                
                # Add element ID text back
                if self.show_trusses_cb.isChecked() and 'element' in row:
                    try:
                        mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
                        ax.text(mx, my, str(int(row['element'])), ha='center', va='center', fontsize=8, bbox=dict(facecolor='white', alpha=0.6), zorder=4)
                    except ValueError:
                        pass
                        
            # Redraw other elements on top of the trusses
            # (Nodes, supports, loads drawing is repeated for a complete visualization)

            # draw nodes
            if not self.points.empty and 'x' in self.points.columns and 'y' in self.points.columns:
                valid_points = self.points.dropna(subset=['x', 'y'])
                if not valid_points.empty:
                    ax.plot(valid_points['x'], valid_points['y'], 'o', markersize=6, color='black', zorder=5)
                
                if self.show_nodes_cb.isChecked() and 'Node' in self.points.columns and self.points['Node'].notnull().all():
                    for _, row in valid_points.iterrows():
                        try:
                            ax.text(row['x'] + 0.02, row['y'] + 0.02, str(int(row['Node'])), fontsize=9, zorder=6)
                        except ValueError:
                            pass 
            
            # draws supports
            for _, row in self.supports.iterrows():
                pos = self.node_coords(row.get('Node'))
                if pos is None: continue
                ax.plot(pos[0], pos[1], 's', color='green', markersize=10, zorder=3)

            # draws loads as arrows
            if not self.loads.empty:
                for _, row in self.loads.iterrows():
                    pos = self.node_coords(row.get('Node'))
                    if pos is None: continue
                    try:
                        fx = float(row.get('Fx', 0.0) or 0.0)
                        fy = float(row.get('Fy', 0.0) or 0.0)
                    except ValueError: continue
                    mag = math.hypot(fx, fy)
                    if mag == 0: continue
                    ux, uy = fx / mag, fy / mag
                    scale = 0.2 * max(0.2, self.zoom_factor() / 10.0)
                    ax.arrow(pos[0], pos[1], ux*scale, uy*scale, head_width=0.08*scale, head_length=0.12*scale, fc='purple', ec='purple', zorder=2)
            
            ax.set_title('Truss Force Visualization (Tension: Blue, Compression: Red)', fontsize=14)
            ax.grid(True)
            self.canvas.fig.tight_layout()
            self.canvas.draw()
            
        except Exception as e:
            QMessageBox.warning(self, "Simulation Error", f"Simulation failed: {str(e)}")
            self.redraw() # Fallback to editor view

    # ---------- File IO (Kept the same) ----------
    def export_design(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose export directory", os.getcwd())
        if not folder:
            return
        try:
            # ensure Node and element columns are present as simple csv-friendly tables
            pts = self.points.copy()
            if 'Node' not in pts.columns:
                pts.insert(0, 'Node', np.arange(1, len(pts) + 1))
            pts.to_csv(os.path.join(folder, 'points.csv'), index=False)
            tr = self.trusses.copy()
            tr.to_csv(os.path.join(folder, 'trusses.csv'), index=False)
            self.supports.to_csv(os.path.join(folder, 'supports.csv'), index=False)
            self.materials.to_csv(os.path.join(folder, 'materials.csv'), index=False)
            self.loads.to_csv(os.path.join(folder, 'loads.csv'), index=False)
            QMessageBox.information(self, "Export", f"Design exported to: {folder}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", str(e))

    def load_design(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose design directory to load", os.getcwd())
        if not folder:
            return
        try:
            pts_path = os.path.join(folder, 'points.csv')
            tr_path = os.path.join(folder, 'trusses.csv')
            sup_path = os.path.join(folder, 'supports.csv')
            mat_path = os.path.join(folder, 'materials.csv')
            loads_path = os.path.join(folder, 'loads.csv')

            # Load data, skipping files that don't exist
            self.points = pd.read_csv(pts_path) if os.path.exists(pts_path) else self.points.iloc[0:0]
            self.trusses = pd.read_csv(tr_path) if os.path.exists(tr_path) else self.trusses.iloc[0:0]
            self.supports = pd.read_csv(sup_path) if os.path.exists(sup_path) else self.supports.iloc[0:0]
            self.materials = pd.read_csv(mat_path) if os.path.exists(mat_path) else self.materials.iloc[0:0]
            self.loads = pd.read_csv(loads_path) if os.path.exists(loads_path) else self.loads.iloc[0:0]

            # repair missing Node column
            if 'Node' not in self.points.columns:
                # if points are just x,y rows, create Node ids
                if 'x' in self.points.columns and 'y' in self.points.columns and not self.points.empty:
                    self.points.insert(0, 'Node', np.arange(1, len(self.points) + 1))
                else:
                    self.points = pd.DataFrame(columns=['Node', 'x', 'y']) # Reset to blank structure

            # reset next id counters
            if not self.points.empty and 'Node' in self.points.columns:
                try:
                    self._next_node_id = int(self.points['Node'].max() + 1)
                except:
                    self._next_node_id = 1
            else:
                self._next_node_id = 1

            if not self.trusses.empty and 'element' in self.trusses.columns:
                try:
                    self._next_element_id = int(self.trusses['element'].max() + 1)
                except:
                    self._next_element_id = 1
            else:
                self._next_element_id = 1

            # refresh table
            self.dataset_changed(self.dataset_combo.currentText())
            self.redraw()
            QMessageBox.information(self, "Load", f"Design loaded from: {folder}")
        except Exception as e:
            QMessageBox.critical(self, "Load Error", str(e))

    def clear_all(self):
        ok = QMessageBox.question(self, "Clear All", "Clear all data? This cannot be undone.", 
                                  QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if ok == QMessageBox.Yes:
            self.points = pd.DataFrame(columns=['Node', 'x', 'y'])
            self.trusses = pd.DataFrame(columns=['element', 'start', 'end'])
            self.supports = pd.DataFrame(columns=['Node', 'type'])
            self.materials = pd.DataFrame(columns=['material', 'E', 'A'])
            self.loads = pd.DataFrame(columns=['Node', 'Fx', 'Fy'])
            self._next_node_id = 1
            self._next_element_id = 1
            # Ensure the current model is updated, which will trigger a redraw
            self.current_model.set_dataframe(self.points) 


if __name__ == '__main__':
    app = QApplication(sys.argv)
    editor = TrussEditor()
    editor.show()
    sys.exit(app.exec_())