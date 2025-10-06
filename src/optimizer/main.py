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
                             QFileDialog, QSplitter, QCheckBox, QSizePolicy) # Added QCheckBox, QSizePolicy
from PySide6.QtCore import Qt, QByteArray # ADDED QByteArray
from PySide6.QtSvgWidgets import QSvgWidget # ADDED QSvgWidget

# Refactored project imports
from .ui_themes import LIGHT_THEME, DARK_THEME
from .ui_components import MplCanvas
from .truss_model import TrussModel
from .optimizer import optimize_truss
from .analysis import get_objective

class OptimizerApp(QMainWindow):
    """Main application window for the truss optimizer."""
    def __init__(self):
        super().__init__()
        
        self.model = None
        self.current_theme = "dark" 
        self.legend_labels = {} 
        
        self.setWindowTitle("Truss Optimizer & Analysis")
        self.setGeometry(100, 100, 1400, 900)

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

        # Apply initial theme styling
        self.setStyleSheet(DARK_THEME)
        self._apply_matplotlib_theme("dark") 
        self._update_legend_colors("dark") 
        self.theme_button.setText("🌞 Light Mode")

        self.status_label.setText("Please select a design directory.")

    # Helper function to load SVG content into QSvgWidget
    def _create_svg_widget(self, svg_content, max_height=None):
        widget = QSvgWidget()
        
        # Convert SVG string to QByteArray
        svg_byte_array = QByteArray(svg_content.encode('utf-8'))
        widget.load(svg_byte_array)
        
        # Let width expand dynamically, fix the height instead
        if max_height is not None:
            widget.setMaximumHeight(max_height)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            # Maintain aspect ratio by setting a fixed width proportional to SVG's viewBox
            # Example: SVG viewBox="0 0 187.938 51.270267"
            svg_width = 187.938
            svg_height = 51.270267
            aspect_ratio = svg_width / svg_height if svg_height > 0 else 1
            widget.setMaximumWidth(int(max_height * aspect_ratio))
        else:
            # By default, allow max height to expand fully in container
            widget.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        
        # Optional: make SVG scale nicely within layout
        # QSvgWidget does not support setAspectRatioMode; use setSizePolicy for scaling
        # The SVG will scale according to the size policy set above
        
        return widget

    def _create_control_panel(self):
        """Creates the left-side control panel."""
        panel = QFrame()
        panel.setMinimumWidth(380)
        panel.setMaximumWidth(480)
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignTop)

        # --- Logo and Theme Toggle (TOP ROW) ---
        top_row_layout = QHBoxLayout()

        # Logo SVG Content
        svg_content = """
        <svg viewBox="0 0 187.938 51.270267" version="1.1" id="svg1" xml:space="preserve" xmlns="http://www.w3.org/2000/svg" xmlns:svg="http://www.w3.org/2000/svg">
            <defs id="defs1"></defs>
            <g id="layer1" style="display: inline" transform="translate(-11.031219,-9.2660847)">
                <path fill="#c72125" d="M 34.489031,25.709256 V 47.738157 H 27.615948 V 25.709256 h -8.049181 v -5.722007 h 22.971445 v 5.722007 z m 34.256982,16.131729 c -0.575538,1.367944 -1.401308,2.54404 -2.477313,3.528296 -1.076003,0.984251 -2.368876,1.743293 -3.87862,2.293807 -1.518086,0.550514 -3.194648,0.825769 -5.046378,0.825769 -1.876754,0 -3.570001,-0.275255 -5.071402,-0.825769 -1.501402,-0.550514 -2.777593,-1.309556 -3.820234,-2.293807 -1.04264,-0.975913 -1.851728,-2.152009 -2.410582,-3.528296 -0.567198,-1.376283 -0.842455,-2.894367 -0.842455,-4.570936 v -17.2828 h 6.83972 v 16.740628 c 0,0.759042 0.100089,1.476381 0.30028,2.15201 0.200186,0.683973 0.508808,1.284534 0.925864,1.826706 0.417057,0.533831 0.967571,0.959229 1.651542,1.27619 0.683972,0.316964 1.509743,0.467104 2.477313,0.467104 0.967568,0 1.793341,-0.158482 2.477312,-0.467104 0.683974,-0.316961 1.242826,-0.734018 1.668226,-1.27619 0.425395,-0.533834 0.734017,-1.142733 0.925862,-1.826706 0.183507,-0.675629 0.283601,-1.40131 0.283601,-2.15201 V 19.987249 h 6.864739 v 17.291142 c 0,1.668227 -0.291938,3.194649 -0.867475,4.562594 z m 5.121446,10.176168 13.94636,-34.165231 H 82.834164 L 68.887812,52.017153 Z M 94.586802,27.702786 c -5.738691,0 -10.393034,4.654344 -10.393034,10.393036 0,5.73869 4.654343,10.393035 10.393034,10.393035 3.686766,0 7.448638,-1.609837 9.475508,-4.512546 l -4.712732,-1.918456 c -1.25116,1.392966 -2.97777,1.94348 -4.762776,1.94348 -2.644132,0 -4.879555,-1.734952 -5.630253,-4.128857 h 15.864821 c 0.10012,-0.575534 0.15014,-1.159412 0.15014,-1.759973 0.009,-5.755375 -4.64602,-10.409719 -10.384708,-10.409719 z m 0,4.495864 c 2.460636,0 4.570936,1.509742 5.455098,3.661751 H 89.131714 c 0.884156,-2.152009 2.994462,-3.661751 5.455088,-3.661751 z"></path>
                <path fill="#c72125" d="m 118.07194,26.397753 v -1.328844 h -2.99445 v -1.337946 h 2.67589 v -1.246928 h -2.67589 v -1.210523 h 2.83062 V 19.95377 h -4.3324 v 6.443983 z m 2.77673,0 V 19.95377 h -1.56548 v 6.443983 z m 7.29998,0 V 19.95377 h -1.51088 l 0.0364,4.204972 h -0.0273 L 124.062,19.95377 h -1.77483 v 6.443983 h 1.51088 l -0.0364,-4.214074 h 0.0273 l 2.59397,4.214074 z m 7.50344,-3.240195 c 0,-2.439247 -1.85674,-3.203788 -3.68618,-3.203788 h -2.33002 v 6.443983 h 2.40284 c 1.77482,0 3.61336,-0.973879 3.61336,-3.240195 z m -1.6201,0 c 0,1.438064 -1.02849,1.893148 -2.13889,1.893148 h -0.73723 v -3.768092 h 0.77364 c 1.07399,0 2.10248,0.427779 2.10248,1.874944 z m 8.33433,3.240195 V 19.95377 h -1.55639 v 2.439248 h -2.51206 V 19.95377 h -1.55638 v 6.443983 h 1.55638 v -2.694095 h 2.51206 v 2.694095 z m 8.16772,-3.249297 c 0,-2.066079 -1.49267,-3.367618 -3.51324,-3.367618 -2.01147,0 -3.50415,1.301539 -3.50415,3.367618 0,2.038775 1.49268,3.422228 3.50415,3.422228 2.02057,0 3.51324,-1.383453 3.51324,-3.422228 z m -1.6656,0 c 0,1.165014 -0.76454,2.002368 -1.84764,2.002368 -1.0831,0 -1.83854,-0.837354 -1.83854,-2.002368 0,-1.128607 0.74634,-1.96596 1.83854,-1.96596 1.0922,0 1.84764,0.837353 1.84764,1.96596 z m 8.25168,-3.194686 h -1.72021 l -1.48357,4.569039 h -0.0364 l -1.49267,-4.569039 h -1.74752 l 2.43924,6.443983 h 1.55639 z m 5.20689,6.443983 v -1.328844 h -2.99445 v -1.337946 h 2.67589 v -1.246928 h -2.67589 v -1.210523 h 2.83062 V 19.95377 h -4.3324 v 6.443983 z m 7.02398,0 V 19.95377 h -1.51087 l 0.0364,4.204972 h -0.0273 l -2.58488,-4.204972 h -1.77482 v 6.443983 h 1.51088 l -0.0364,-4.214074 h 0.0273 l 2.59398,4.214074 z"></path>
                <path fill="#c72125" d="m 119.09111,34.653049 v -4.013837 h -1.55639 v 3.886413 c 0,0.691727 -0.32766,1.328844 -1.21052,1.328844 -0.87376,0 -1.21052,-0.637117 -1.21052,-1.328844 v -3.886413 h -1.54729 v 4.013837 c 0,1.547284 1.0558,2.603077 2.74871,2.603077 1.68381,0 2.77601,-1.055793 2.77601,-2.603077 z m 7.26371,2.430146 v -6.443983 h -1.51088 l 0.0364,4.204972 h -0.0273 l -2.58488,-4.204972 h -1.77482 v 6.443983 h 1.51087 l -0.0364,-4.214074 h 0.0273 l 2.59398,4.214074 z m 3.01617,0 v -6.443983 h -1.56548 v 6.443983 z m 7.14231,-6.443983 h -1.72021 l -1.48358,4.569039 h -0.0364 l -1.49268,-4.569039 h -1.74752 l 2.43925,6.443983 h 1.55639 z m 5.23126,6.443983 v -1.328844 h -2.99445 v -1.337946 h 2.67589 v -1.246928 h -2.67589 v -1.210523 h 2.83062 v -1.319742 h -4.3324 v 6.443983 z m 6.48111,0 -1.68381,-2.757806 c 0.82826,-0.254847 1.33795,-0.873761 1.33795,-1.738419 0,-1.474471 -1.22873,-1.947758 -2.46655,-1.947758 h -2.45745 v 6.443983 h 1.52908 v -2.55757 h 0.52789 l 1.39256,2.55757 z m -1.88404,-4.46892 c 0,0.65532 -0.62802,0.782743 -1.12861,0.782743 h -0.73724 v -1.501775 h 0.82826 c 0.46418,0 1.03759,0.118321 1.03759,0.719032 z m 7.19089,-1.347048 c -0.5643,-0.518795 -1.38345,-0.791845 -2.11159,-0.791845 -1.20142,0 -2.49385,0.591609 -2.49385,2.020571 0,1.165014 0.82825,1.583691 1.6474,1.847639 0.84645,0.27305 1.33794,0.427778 1.33794,0.919269 0,0.518795 -0.41867,0.700828 -0.89196,0.700828 -0.50969,0 -1.0831,-0.291253 -1.39256,-0.682625 l -1.01938,1.03759 c 0.5643,0.591609 1.49267,0.928371 2.41194,0.928371 1.27423,0 2.46655,-0.664422 2.46655,-2.147994 0,-1.283336 -1.1286,-1.656504 -2.00236,-1.938656 -0.60982,-0.191135 -0.99209,-0.32766 -0.99209,-0.755439 0,-0.509693 0.5006,-0.646218 0.90107,-0.646218 0.40047,0 0.88286,0.21844 1.14681,0.555202 z m 2.65813,5.815968 v -6.443983 h -1.56549 v 6.443983 z m 6.01664,-5.115139 v -1.328844 h -5.19706 v 1.328844 h 1.82034 v 5.115139 h 1.55638 v -5.115139 z m 6.85269,-1.328844 h -1.82034 l -1.37435,2.384638 -1.37435,-2.384638 h -1.88405 l 2.42105,3.713482 v 2.730501 h 1.55638 v -2.730501 z m 9.74376,3.194686 c 0,-2.066079 -1.49268,-3.367618 -3.51325,-3.367618 -2.01147,0 -3.50414,1.301539 -3.50414,3.367618 0,2.038775 1.49267,3.422228 3.50414,3.422228 2.02057,0 3.51325,-1.383453 3.51325,-3.422228 z m -1.66561,0 c 0,1.165014 -0.76454,2.002368 -1.84764,2.002368 -1.0831,0 -1.83853,-0.837354 -1.83853,-2.002368 0,-1.128607 0.74633,-1.96596 1.83853,-1.96596 1.0922,0 1.84764,0.837353 1.84764,1.96596 z m 7.0695,-1.865842 v -1.328844 h -4.24137 v 6.443983 h 1.53818 v -2.50296 h 2.49386 V 33.2969 h -2.49386 v -1.328844 z"></path>
                <path fill="#c72125" d="m 118.74707,42.669827 v -1.328844 h -5.19705 v 1.328844 h 1.82033 v 5.115139 h 1.55639 v -5.115139 z m 5.30363,5.115139 v -1.328844 h -2.99445 v -1.337946 h 2.67589 v -1.246929 h -2.67589 v -1.210522 h 2.83062 v -1.319742 h -4.3324 v 6.443983 z m 6.75974,-0.891964 -1.0831,-1.019387 c -0.27305,0.38227 -0.75544,0.65532 -1.36525,0.65532 -1.074,0 -1.82944,-0.800947 -1.82944,-1.975062 0,-1.137709 0.77365,-1.975063 1.85674,-1.975063 0.49149,0 1.01029,0.191135 1.30154,0.591609 l 1.0558,-1.055794 c -0.537,-0.618914 -1.51088,-0.946574 -2.41195,-0.946574 -1.96596,0 -3.49504,1.319742 -3.49504,3.385822 0,2.02057 1.48358,3.404024 3.46774,3.404024 1.0831,0 1.93866,-0.409575 2.50296,-1.064895 z m 6.39891,0.891964 v -6.443983 h -1.55639 v 2.439248 h -2.51206 v -2.439248 h -1.55638 v 6.443983 h 1.55638 v -2.694095 h 2.51206 v 2.694095 z m 7.27561,0 v -6.443983 h -1.51088 l 0.0364,4.204972 h -0.0273 l -2.58488,-4.204972 h -1.77482 v 6.443983 h 1.51087 l -0.0364,-4.214074 h 0.0273 l 2.59398,4.214074 z m 8.1799,-3.249297 c 0,-2.066079 -1.49267,-3.367618 -3.51324,-3.367618 -2.01147,0 -3.50414,1.301539 -3.50414,3.367618 0,2.038774 1.49267,3.422228 3.50414,3.422228 2.02057,0 3.51324,-1.383454 3.51324,-3.422228 z m -1.6656,0 c 0,1.165014 -0.76454,2.002368 -1.84764,2.002368 -1.0831,0 -1.83854,-0.837354 -1.83854,-2.002368 0,-1.128607 0.74634,-1.965961 1.83854,-1.965961 1.0922,0 1.84764,0.837354 1.84764,1.965961 z m 6.87528,3.249297 v -1.356149 h -2.49385 v -5.087834 h -1.56549 v 6.443983 z m 7.42079,-3.249297 c 0,-2.066079 -1.49267,-3.367618 -3.51324,-3.367618 -2.01147,0 -3.50415,1.301539 -3.50415,3.367618 0,2.038774 1.49268,3.422228 3.50415,3.422228 2.02057,0 3.51324,-1.383454 3.51324,-3.422228 z m -1.66561,0 c 0,1.165014 -0.76454,2.002368 -1.84763,2.002368 -1.0831,0 -1.83854,-0.837354 -1.83854,-2.002368 0,-1.128607 0.74634,-1.965961 1.83854,-1.965961 1.0922,0 1.84763,0.837354 1.84763,1.965961 z m 8.49216,2.857925 v -3.413127 h -2.65769 v 1.256031 h 1.22873 v 1.174115 c -0.27305,0.118322 -0.60982,0.172932 -0.97388,0.172932 -1.26513,0 -1.96596,-0.846455 -1.96596,-2.029672 0,-1.155913 0.80094,-2.01147 1.89314,-2.01147 0.62802,0 1.14681,0.254847 1.44717,0.600711 l 0.98298,-1.119506 c -0.537,-0.518795 -1.47447,-0.855557 -2.48476,-0.855557 -1.96596,0 -3.49504,1.319742 -3.49504,3.385822 0,2.029672 1.48357,3.394923 3.54055,3.394923 0.99208,0 1.85674,-0.227542 2.48476,-0.555202 z m 6.91741,-6.052611 h -1.82034 l -1.37435,2.384638 -1.37435,-2.384638 h -1.88405 l 2.42105,3.713481 v 2.730502 h 1.55638 v -2.730502 z"></path>
            </g>
        </svg>
        """
        
        # USE QSvgWidget and helper function
        # Fixed width ensures it fits the panel and scales correctly
        self.logo_widget = self._create_svg_widget(svg_content, max_height=40)
        self.logo_widget.setStyleSheet("background: transparent;")  # Ensure transparent background
        
        # Theme Toggle
        self.theme_button = QPushButton() 
        self.theme_button.clicked.connect(self.toggle_theme)
        self.theme_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Add logo and button to the top row layout
        top_row_layout.addWidget(self.logo_widget)
        top_row_layout.addStretch(1) # Pushes the button to the right
        top_row_layout.addWidget(self.theme_button)
        
        # Add the top row layout to the main control panel layout
        layout.addLayout(top_row_layout)
        # --- END Logo and Theme Toggle ---


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
        
        # Plot Toggles
        toggle_group = QFrame()
        toggle_layout = QVBoxLayout(toggle_group)
        toggle_layout.addWidget(QLabel("<b>Plot Toggles</b>"))
        
        self.show_nodes_cb = QCheckBox("Show Node IDs")
        self.show_nodes_cb.setChecked(True)
        self.show_nodes_cb.stateChanged.connect(self._draw_truss)
        toggle_layout.addWidget(self.show_nodes_cb)

        self.show_trusses_cb = QCheckBox("Show Truss Element IDs")
        self.show_trusses_cb.setChecked(False)
        self.show_trusses_cb.stateChanged.connect(self._draw_truss)
        toggle_layout.addWidget(self.show_trusses_cb)
        
        layout.addWidget(toggle_group)


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
        """Creates the right-side visualization panel, including the Matplotlib canvas and tabs."""
        panel = QFrame()
        layout = QVBoxLayout(panel)
        self.tab_widget = QTabWidget()
        
        # Initialize Matplotlib canvas and tables
        self.truss_canvas = MplCanvas()
        self.metrics_table = QTableWidget(0, 2)
        self.metrics_table.setHorizontalHeaderLabels(['Metric', 'Value'])
        self.final_points_table = QTableWidget(0, 3)
        self.final_points_table.setHorizontalHeaderLabels(['Node ID', 'x', 'y'])
        
        self.tab_widget.addTab(self.truss_canvas, "2D Truss Plot")
        self.tab_widget.addTab(self.metrics_table, "Metrics")
        self.tab_widget.addTab(self.final_points_table, "Final Positions")
        layout.addWidget(self.tab_widget)
        
        # Constraints Legend (Bottom Panel)
        legend_frame = QFrame()
        legend_frame.setFrameShape(QFrame.StyledPanel)
        legend_layout = QHBoxLayout(legend_frame)
        legend_layout.setAlignment(Qt.AlignCenter)
        
        def create_symbol_label(symbol, color):
            style = f"""
            QLabel {{
                background-color: transparent;
                font-size: 14pt; 
                font-weight: bold;
                padding-right: 5px;
            }}
            """
            if symbol == 's': symbol_text = '■'
            elif symbol == 'D': symbol_text = '◆'
            else: symbol_text = symbol
            label = QLabel(symbol_text)
            label.setStyleSheet(style + f"color:{color};")
            return label

        # Create Legend Labels and store references in self.legend_labels
        self.legend_labels['header'] = QLabel("<b>Legend:</b>")
        self.legend_labels['pin_sym'] = create_symbol_label('s', 'green')
        self.legend_labels['pin_text'] = QLabel("Pin/Fixed (Rx=1, Ry=1)")
        self.legend_labels['roller_sym'] = create_symbol_label('D', 'darkgreen')
        self.legend_labels['roller_text'] = QLabel("Roller (Rx=0 or Ry=0)")
        self.legend_labels['member_header'] = QLabel("| <b>Member Forces:</b>")
        self.legend_labels['tension'] = QLabel("| <span style='color:blue;'>Tension (T)</span>")
        self.legend_labels['compression'] = QLabel("| <span style='color:red;'>Compression (C)</span>")
        self.legend_labels['load_header'] = QLabel("| <b>Loads:</b>")
        self.legend_labels['load_text'] = QLabel("<span style='color:purple;'>Applied Load</span>")
        
        # Add labels to layout
        for key in ['header', 'pin_sym', 'pin_text', 'roller_sym', 'roller_text', 
                    'member_header', 'tension', 'compression', 'load_header', 'load_text']:
            legend_layout.addWidget(self.legend_labels[key])
        
        layout.addWidget(legend_frame)
        
        return panel

    def _update_legend_colors(self, theme_name):
        """
        Helper to update the colors of the non-symbol legend text labels.
        FIXED: Prevents injecting style XML into existing text.
        """
        base_color = "white" if theme_name == "dark" else "black"
        
        # Keys for labels whose text color needs to change based on the theme
        theme_dependent_keys = ['header', 'pin_text', 'roller_text', 'member_header', 'load_header']
        
        style = f"color:{base_color};"
        
        for key in theme_dependent_keys:
            if key in self.legend_labels:
                label = self.legend_labels[key]
                # Apply the color via stylesheet for all labels. 
                label.setStyleSheet(style)


    def toggle_theme(self):
        # Swap theme name
        self.current_theme = "dark" if self.current_theme == "light" else "light"
        self.apply_theme(self.current_theme)

    def apply_theme(self, theme_name):
        # 1. Apply Qt Stylesheet (Fixes issue with light mode not loading)
        self.setStyleSheet(LIGHT_THEME if theme_name == "light" else DARK_THEME)
        
        # 2. Update button text
        self.theme_button.setText("🌞 Light Mode" if theme_name == "dark" else "🌙 Dark Mode")
        
        # 3. Apply Matplotlib theme
        self._apply_matplotlib_theme(theme_name)
        
        # 4. Update Legend text colors
        self._update_legend_colors(theme_name)
        

    def _apply_matplotlib_theme(self, theme_name):
        is_dark = theme_name == "dark"
        bg_color = "#2b2b2b" if is_dark else "#ffffff"
        fg_color = "white" if is_dark else "black" # Text color (point labels, axes, title)
        
        self.truss_canvas.fig.patch.set_facecolor(bg_color)
        ax = self.truss_canvas.axes
        ax.set_facecolor(bg_color)
        ax.tick_params(colors=fg_color, which="both")
        for spine in ax.spines.values(): spine.set_color(fg_color)
        ax.xaxis.label.set_color(fg_color)
        ax.yaxis.label.set_color(fg_color)
        ax.title.set_color(fg_color)
        
        # Re-draw the truss to apply new label colors
        if self.model: 
            self._draw_truss()
        else: 
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
        
        # FIX: Ensure plot is rendered immediately on load
        self._draw_truss()
        self.truss_canvas.draw()
        
    def _draw_truss(self):
        """Draws the current truss from self.model on the canvas with toggles and theme applied."""
        if not self.model: return
        
        ax = self.truss_canvas.axes
        ax.clear()
        
        points_df = self.model.points
        trusses_df = self.model.trusses
        stresses_df = self.model.stresses_df
        supports_df = self.model.supports
        loads_df = self.model.loads
        
        # Color for text labels based on theme
        label_color = "white" if self.current_theme == "dark" else "black"

        # Plot members (Trusses)
        for _, row in trusses_df.iterrows():
            try:
                p1 = points_df.loc[points_df['Node'] == row['start'], ['x', 'y']].values[0]
                p2 = points_df.loc[points_df['Node'] == row['end'], ['x', 'y']].values[0]
            except IndexError:
                continue
            
            force = 0
            try:
                force_row = stresses_df.loc[stresses_df['element'] == row['element'], 'axial_force']
                if not force_row.empty:
                    force = force_row.iloc[0]
                    color = 'red' if force < 0 else 'blue' # Compression (C) is red, Tension (T) is blue
                else:
                    color = 'gray'
            except (KeyError, IndexError):
                color = 'gray'
            
            ax.plot([p1[0], p2[0]], [p1[1], p2[1]], color=color, linewidth=2)
            
            if self.show_trusses_cb.isChecked():
                mid_x = (p1[0] + p2[0]) / 2
                mid_y = (p1[1] + p2[1]) / 2
                ax.text(mid_x, mid_y, str(int(row['element'])), 
                        ha='center', va='center', fontsize=6, color=label_color,
                        bbox=dict(facecolor='black' if self.current_theme == 'dark' else 'white', 
                                  alpha=0.7, edgecolor='none', pad=1))

        # Plot nodes
        ax.plot(points_df['x'], points_df['y'], 'o', color=label_color, zorder=5, markersize=5)
        
        # Plot node labels
        if self.show_nodes_cb.isChecked():
            span_x = points_df['x'].max() - points_df['x'].min()
            span_y = points_df['y'].max() - points_df['y'].min()
            max_span = max(span_x, span_y) if span_x > 0 or span_y > 0 else 1
            label_offset_distance = max_span * 0.015 
            
            for _, row in points_df.iterrows():
                node_id = row['Node'] 
                ax.text(row['x'] + label_offset_distance, 
                        row['y'] + label_offset_distance, 
                        str(int(node_id)), 
                        ha='left', va='bottom', fontsize=8, fontweight='bold', 
                        color=label_color, zorder=8) 

        # Plot supports
        if not supports_df.empty and all(col in supports_df.columns for col in ['Node', 'Rx', 'Ry']):
            for _, row in supports_df.iterrows():
                try:
                    node_pos = points_df.loc[points_df['Node'] == row['Node'], ['x', 'y']].values[0]
                    
                    Rx = row['Rx']
                    Ry = row['Ry']
                    
                    if Rx == 1 and Ry == 1:
                        # Fixed Support
                        support_marker = 's' 
                        color = 'green'
                    elif (Rx == 0 and Ry == 1) or (Rx == 1 and Ry == 0):
                        # Roller Support (in X or Y direction)
                        support_marker = 'D'
                        color = 'darkgreen'
                    else:
                        # No support or unhandled combination
                        continue
                        
                    ax.plot(node_pos[0], node_pos[1], support_marker, color=color, markersize=12, zorder=6)
                except (IndexError, KeyError) as e:
                    print(f"Error plotting support: {e}. Check your supports data structure.")
                    continue
        else:
            print("Warning: supports_df is empty or missing 'Node', 'Rx', or 'Ry' columns. Skipping support plot.")
            
        # Plot loads 
        if loads_df is not None and not loads_df.empty:
            max_truss_span = max(points_df['x'].max() - points_df['x'].min(), 
                                points_df['y'].max() - points_df['y'].min())
            if max_truss_span <= 0: max_truss_span = 1.0

            arrow_scale = max_truss_span * 0.1 
                
            for _, row in loads_df.iterrows():
                try:
                    node_pos = points_df.loc[points_df['Node'] == row['Node'], ['x', 'y']].values[0]
                    fx, fy = row.get('Fx', 0), row.get('Fy', 0)
                    
                    force_magnitude = np.sqrt(fx**2 + fy**2)
                    if force_magnitude > 0:
                        unit_fx, unit_fy = fx / force_magnitude, fy / force_magnitude
                        arrow_dx = unit_fx * arrow_scale
                        arrow_dy = unit_fy * arrow_scale
                        
                        ax.arrow(
                            node_pos[0], node_pos[1], 
                            arrow_dx, arrow_dy,
                            head_width=0.05 * arrow_scale, head_length=0.075 * arrow_scale, 
                            fc='purple', ec='purple', linewidth=2, zorder=7
                        )
                except IndexError:
                    continue


        ax.set_title("Truss Diagram", color=label_color)
        ax.set_xlabel("X-coordinate (m)", color=label_color)
        ax.set_ylabel("Y-coordinate (m)", color=label_color)
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
    
    if is_standalone:
        window.show()
        sys.exit(app.exec())
    
    return window

if __name__ == '__main__':
    main()