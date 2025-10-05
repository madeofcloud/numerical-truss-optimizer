import sys
# subprocess import REMOVED
from PySide6.QtCore import Qt, QPoint, QSize, QByteArray
from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QDialog, QSlider,
    QFrame
)

import editor
import optimizer_app
import visualizer

# --- Global Style Sheet ---
APP_STYLESHEET = """
QMainWindow, QDialog {
    background-color: #1e1e1e;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QLabel { color: #d0d0d0; }
QLabel#TitleLabel { font-size: 24px; font-weight: bold; color: #ffffff; }
QLabel#SubtitleLabel { font-size: 14px; color: #a0a0a0; }
QPushButton {
    background-color: #2d2d2d;
    color: #f0f0f0;
    border: 1px solid #444;
    border-radius: 15px;
    font-size: 16px;
    font-weight: bold;
    text-align: left;
    padding-left: 12px;
    padding-top: 12px;
    padding-bottom: 12px;
}
QPushButton:hover {
    background-color: #383838;
}
QPushButton:pressed {
    background-color: #1e1e1e;
}
"""

# --- SVG Icons ---
# SVG_EDIT = """<svg fill="#f0f0f0" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>"""
# SVG_OPTIMIZE = """<svg fill="#f0f0f0" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/></svg>"""
# SVG_VISUALIZE = """<svg fill="#f0f0f0" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zm0 13c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/></svg>"""
# SVG_CHEVRON = """<svg fill="#f0f0f0" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/></svg>"""
SVG_COLOR = "#f0f0f0"
SVG_EDIT = f"""<svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="{SVG_COLOR}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
<path d="M13 7 8.7 2.7a2.41 2.41 0 0 0-3.4 0L2.7 5.3a2.41 2.41 0 0 0 0 3.4L7 13"/>
<path d="m8 6 2-2"/>
<path d="m18 16 2-2"/>
<path d="m17 11 4.3 4.3c.94.94.94 2.46 0 3.4l-2.6 2.6c-.94.94-2.46.94-3.4 0L11 17"/>
<path d="M21.174 6.812a1 1 0 0 0-3.986-3.987L3.842 16.174a2 2 0 0 0-.5.83l-1.321 4.352a.5.5 0 0 0 .623.622l4.353-1.32a2 2 0 0 0 .83-.497z"/>
<path d="m15 5 4 4"/>
</svg>"""
SVG_OPTIMIZE = f"""<svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="{SVG_COLOR}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
<circle cx="7.5" cy="7.5" r=".5" fill="{SVG_COLOR}"/>
<circle cx="18.5" cy="5.5" r=".5" fill="{SVG_COLOR}"/>
<circle cx="11.5" cy="11.5" r=".5" fill="{SVG_COLOR}"/>
<circle cx="7.5" cy="16.5" r=".5" fill="{SVG_COLOR}"/>
<circle cx="17.5" cy="14.5" r=".5" fill="{SVG_COLOR}"/>
<path d="M3 3v16a2 2 0 0 0 2 2h16"/>
</svg>"""
SVG_VISUALIZE = f"""<svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="{SVG_COLOR}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
<path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z"/>
<path d="M14 2v4a2 2 0 0 0 2 2h4"/>
<circle cx="10" cy="12" r="2"/>
<path d="m20 17-1.296-1.296a2.41 2.41 0 0 0-3.408 0L9 22"/>
</svg>"""
SVG_CLOSE = """<svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
<path d="M18 6 6 18"/><path d="m6 6 12 12"/>
</svg>"""
SVG_CHEVRON = """<svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="{SVG_COLOR}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
<path d="m9 18 6-6-6-6"/>
</svg>"""


def svg_to_icon(svg_content, size):
    """Converts SVG content string to a QIcon using QSvgRenderer."""
    renderer = QSvgRenderer(QByteArray(svg_content.encode('utf-8')))
    pixmap = QPixmap(size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

class RoundedWindow(QWidget):
    """Base class for a frameless, rounded, draggable window."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.oldPos = self.pos()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect().adjusted(1, 1, -1, -1) # adjust for border
        color = QColor("#1e1e1e") # <-- QColor is now defined
        color.setAlpha(255) 
        painter.setBrush(color)
        painter.setPen(QColor("#333333"))
        
        radius = 20
        painter.drawRoundedRect(rect, radius, radius)
        painter.end() # <-- Explicitly end the painter here

class MainWindow(RoundedWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Truss Suite Launcher")
        self.setGeometry(100, 100, 400, 500)
        
        # Store references to active sub-applications to prevent garbage collection
        self.active_apps = [] 

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(15)

        # Title
        title_label = QLabel("Truss Analysis Suite")
        title_label.setObjectName("TitleLabel")
        main_layout.addWidget(title_label)

        subtitle_label = QLabel("Select an application to launch:")
        subtitle_label.setObjectName("SubtitleLabel")
        main_layout.addWidget(subtitle_label)

        main_layout.addSpacing(20)

        # Launch Buttons
        btn_editor = self._create_launch_button("Design Editor", SVG_EDIT, self.launch_editor)
        btn_optimizer = self._create_launch_button("Numerical Optimizer", SVG_OPTIMIZE, self.launch_optimizer_dialog)
        btn_visualizer = self._create_launch_button("Result Visualizer", SVG_VISUALIZE, self.launch_visualizer)
        
        main_layout.addWidget(btn_editor)
        main_layout.addWidget(btn_optimizer)
        main_layout.addWidget(btn_visualizer)

        main_layout.addStretch()

        # Exit button (optional, but good practice for frameless windows)
        exit_button = QPushButton("Exit")
        exit_button.setStyleSheet("background-color: #c0392b; border: none; padding: 10px; border-radius: 10px;")
        exit_button.clicked.connect(self.close)
        main_layout.addWidget(exit_button)
        
        self.setLayout(main_layout)

    def _create_launch_button(self, text, svg_icon, handler):
        button = QPushButton()
        button.clicked.connect(handler)
        
        layout = QHBoxLayout(button)
        layout.setContentsMargins(15, 0, 15, 0)
        layout.setSpacing(10)
        
        icon_label = QLabel()
        icon_label.setPixmap(svg_to_icon(svg_icon, QSize(32, 32)).pixmap(32, 32))
        layout.addWidget(icon_label)

        text_label = QLabel(text)
        text_label.setStyleSheet("color:#f0f0f0; font-weight:bold; text-align: left;")
        layout.addWidget(text_label, 1, Qt.AlignVCenter)

        chevron_label = QLabel()
        chevron_label.setPixmap(svg_to_icon(SVG_CHEVRON, QSize(24, 24)).pixmap(24, 24))
        layout.addWidget(chevron_label)

        return button

    def launch_editor(self):
        print("Launching Editor...")
        # Direct class instantiation using the existing QApplication
        # The main() function in editor.py now returns the window instance
        app_window = editor.main() 
        self.active_apps.append(app_window) # Keep reference to prevent garbage collection
        app_window.show()
        # self.close() # Keep launcher open

    def launch_optimizer_dialog(self):
        print("Launching Optimizer...")
        # Direct class instantiation
        app_window = optimizer_app.main() # optimizer_app.main() returns OptimizerApp instance
        self.active_apps.append(app_window) # Keep reference
        app_window.show()
        # self.close() # Keep launcher open

    def launch_visualizer(self):
        print("Launching Visualizer...")
        # Direct class instantiation
        app_window = visualizer.main() # visualizer.main() returns TrussRenderer instance
        self.active_apps.append(app_window) # Keep reference
        app_window.show()
        # self.close() # Keep launcher open

    def mousePressEvent(self, event):
        self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPosition().toPoint() - self.oldPos)
        self.move(self.pos() + delta)
        self.oldPos = event.globalPosition().toPoint()
        
    def closeEvent(self, event):
        # When the launcher closes, close all active sub-apps as well
        for app in self.active_apps:
            if app.isVisible():
                app.close()
        super().closeEvent(event)


if __name__ == '__main__':
    # 1. Check if a QApplication instance already exists
    app = QApplication.instance()
    if app is None:
        # 2. If not, create a new one
        app = QApplication(sys.argv)
    
    app.setStyleSheet(APP_STYLESHEET)
    
    main_window = MainWindow()
    main_window.show()
    
    # Run the main application event loop
    sys.exit(app.exec())