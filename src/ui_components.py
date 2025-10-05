from PySide6.QtWidgets import QWidget # Changed from PyQt5.QtWidgets
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas # Changed from backend_qt5agg
from matplotlib.figure import Figure
from mpl_toolkits.mplot3d import Axes3D

class MplCanvas(FigureCanvas):
    """A custom class to embed a Matplotlib figure into a PyQt widget."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111)
        # Note: super(MplCanvas, self) is Python 2 style, use super().__init__ in modern Python,
        # but maintaining the old syntax for compatibility with your existing structure.
        super(MplCanvas, self).__init__(self.fig)
        self.setParent(parent)

class Mpl3DCanvas(FigureCanvas):
    """A custom class to embed a 3D Matplotlib figure into a PyQt widget."""
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        self.axes = self.fig.add_subplot(111, projection='3d')
        super(Mpl3DCanvas, self).__init__(self.fig)
        self.setParent(parent)
