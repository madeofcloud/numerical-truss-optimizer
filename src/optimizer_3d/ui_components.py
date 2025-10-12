from PySide6.QtWidgets import QWidget
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D # Required for 'projection='3d'
import numpy as np

class Mpl3DCanvas(FigureCanvas):
    """
    A custom class to embed a 3D Matplotlib figure into a PyQt widget.
    Includes mouse scroll handling for zooming.
    """
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        
        # Explicitly create a 3D subplot
        self.axes = self.fig.add_subplot(111, projection='3d') 
        
        super(Mpl3DCanvas, self).__init__(self.fig)
        self.setParent(parent)
        
        # Connect mouse scroll event for zooming
        self.fig.canvas.mpl_connect('scroll_event', self.on_scroll)

    def on_scroll(self, event):
        """Handle mouse scroll event for zooming in/out in 3D."""
        ax = self.axes
        
        # Get current limits
        xlim = ax.get_xlim3d()
        ylim = ax.get_ylim3d()
        zlim = ax.get_zlim3d()
        
        # Calculate the center point
        center_x = (xlim[0] + xlim[1]) / 2
        center_y = (ylim[0] + ylim[1]) / 2
        center_z = (zlim[0] + zlim[1]) / 2
        
        # Calculate the range
        range_x = xlim[1] - xlim[0]
        range_y = ylim[1] - ylim[0]
        range_z = zlim[1] - zlim[0]

        # Define the zoom factor (1.1 for zoom in, 1/1.1 for zoom out)
        zoom_factor = 1.1 if event.button == 'up' else 1/1.1 
        
        # Calculate new ranges
        new_range_x = range_x / zoom_factor
        new_range_y = range_y / zoom_factor
        new_range_z = range_z / zoom_factor

        # Set new limits, keeping the center constant
        ax.set_xlim3d(center_x - new_range_x / 2, center_x + new_range_x / 2)
        ax.set_ylim3d(center_y - new_range_y / 2, center_y + new_range_y / 2)
        ax.set_zlim3d(center_z - new_range_z / 2, center_z + new_range_z / 2)
        
        self.draw()

    def update_theme(self, theme_config):
        """
        Updates the figure and axes colors based on the selected theme configuration.
        """
        bg_color = theme_config['bg_color_hex']
        text_color = theme_config['text_color_hex']

        # 1. Update Figure (Background behind the axes)
        self.fig.patch.set_facecolor(bg_color)
        
        # 2. Update Axes (The plotting area's background and pane colors)
        ax = self.axes
        
        # Set the color of the 3D planes (x, y, z background)
        ax.xaxis.set_pane_color((0.9, 0.9, 0.9, 0.0) if bg_color == '#FFFFFF' else (0.1, 0.1, 0.1, 0.0))
        ax.yaxis.set_pane_color((0.9, 0.9, 0.9, 0.0) if bg_color == '#FFFFFF' else (0.1, 0.1, 0.1, 0.0))
        ax.zaxis.set_pane_color((0.9, 0.9, 0.9, 0.0) if bg_color == '#FFFFFF' else (0.1, 0.1, 0.1, 0.0))
        
        # Set the color of the main axes background (this is often transparent in 3D)
        ax.set_facecolor(bg_color)

        # 3. Update Text (Labels, Ticks, and Title)
        
        # Set tick label color for all axes
        ax.tick_params(axis='x', colors=text_color)
        ax.tick_params(axis='y', colors=text_color)
        ax.tick_params(axis='z', colors=text_color)

        # Set label color (X, Y, Z labels)
        ax.xaxis.label.set_color(text_color)
        ax.yaxis.label.set_color(text_color)
        ax.zaxis.label.set_color(text_color)

        # Set title color
        ax.title.set_color(text_color)

        # Explicitly set the color of the axis lines and tick markers
        # Matplotlib 3D often uses different objects for the spines
        ax.w_xaxis.line.set_color(text_color)
        ax.w_yaxis.line.set_color(text_color)
        ax.w_zaxis.line.set_color(text_color)
        
        # Re-apply a consistent background color to avoid Matplotlib's default white figure.
        self.fig.set_facecolor(bg_color)
        
        # Since the truss drawing logic might also rely on the theme, 
        # it's usually best to call the main drawing function after changing the theme 
        # (which is already done in main_3d.py's _toggle_theme method).
# Removed the unused MplCanvas class to simplify the file.
