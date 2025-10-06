import sys
from PySide6.QtCore import Qt, QPoint, QSize, QByteArray, QRectF
from PySide6.QtGui import QPixmap, QIcon, QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QWidget, QDialog, QSlider,
    QFrame, QSizePolicy, QListWidget, QListWidgetItem
)

from editor.main import main as editor_main
from optimizer.main import main as optimizer_main
from visualizer.main import main as visualizer_main

# --- Global Style Sheet ---
APP_STYLESHEET = """
QMainWindow, QDialog, QWidget#RoundedWindow {
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
/* Style for disabled buttons */
QPushButton:disabled {
    background-color: #1a1a1a; /* Darker background */
    color: #6a6a6a; /* Grayed out text */
    border: 1px solid #333;
}
/* Style for the Active Apps List */
QListWidget {
    background-color: #2d2d2d;
    border: 1px solid #444;
    border-radius: 10px;
    color: #f0f0f0;
    padding: 5px;
}
QListWidget::item {
    padding: 5px;
}
QListWidget::item:selected {
    background-color: #383838;
}
"""

# --- SVG Icons ---
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
SVG_CHEVRON = f"""<svg xmlns="http://www.w3.org/2000/svg" fill="none" stroke="{SVG_COLOR}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" viewBox="0 0 24 24">
<path d="m9 18 6-6-6-6"/>
</svg>"""

# --- Utility Functions (unchanged) ---

def svg_to_icon(svg_content, size):
    """Converts SVG content string to a QIcon using QSvgRenderer."""
    renderer = QSvgRenderer(QByteArray(svg_content.encode('utf-8')))
    pixmap = QPixmap(size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

def svg_to_pixmap(svg_content, max_width=140, max_height=40):
    """Render SVG to a QPixmap that fits within max_width x max_height while
    preserving aspect ratio and avoiding clipping."""
    renderer = QSvgRenderer(QByteArray(svg_content.encode('utf-8')))

    # Try to get the SVG's viewBox; fall back to defaultSize if needed
    vb = renderer.viewBoxF()
    if not vb.isNull() and vb.width() > 0 and vb.height() > 0:
        w0 = vb.width()
        h0 = vb.height()
    else:
        ds = renderer.defaultSize()
        w0 = ds.width() or 100
        h0 = ds.height() or 30

    scale = min(max_width / w0, max_height / h0)
    target_w = max(1, int(round(w0 * scale)))
    target_h = max(1, int(round(h0 * scale)))

    pixmap = QPixmap(QSize(target_w, target_h))
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter, QRectF(0, 0, target_w, target_h))
    painter.end()
    return pixmap

# --- RoundedWindow (unchanged) ---

class RoundedWindow(QWidget):
    """Base class for a frameless, rounded, draggable window."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("RoundedWindow") # Added for stylesheet targeting
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.oldPos = self.pos()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect().adjusted(1, 1, -1, -1) # adjust for border
        color = QColor("#1e1e1e")
        color.setAlpha(255) 
        painter.setBrush(color)
        painter.setPen(QColor("#333333"))
        
        radius = 20
        painter.drawRoundedRect(rect, radius, radius)
        painter.end()

# --- MainWindow (Modified) ---

class MainWindow(RoundedWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Truss Suite Launcher")
        self.setGeometry(100, 100, 400, 600) # Increased height to accommodate new section
        
        # Dictionary to store active applications with their app_id as key
        # Value is a tuple: (window_instance, button_instance, list_item)
        self.active_apps = {} 
        self.APP_IDS = {
            "editor": ("Design Editor", SVG_EDIT, self.launch_editor),
            "optimizer": ("Numerical Optimizer", SVG_OPTIMIZE, self.launch_optimizer),
            "visualizer": ("Result Visualizer", SVG_VISUALIZE, self.launch_visualizer)
        }
        self.buttons = {} # Store buttons by ID

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(30, 30, 30, 30)
        main_layout.setSpacing(15)

        # Title/Logo Section (Unchanged)
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_label = QLabel("Truss Analysis Suite")
        title_label.setObjectName("TitleLabel")
        title_row.addWidget(title_label, 1, Qt.AlignVCenter)
        # The original SVG you provided (kept intact)
        SVG_LOGO = """<?xml version="1.0" encoding="UTF-8"?>
        <svg version="1.1" xmlns="http://www.w3.org/2000/svg" width="500" height="200">
        <path d="M0 0 C13.86 0 27.72 0 42 0 C42.0093457 3.18374268 42.01869141 6.36748535 42.02832031 9.64770508 C42.06216001 20.19300968 42.11774803 30.73812004 42.18390274 41.28326893 C42.22333094 47.67380072 42.25554247 54.06419568 42.27099609 60.45483398 C42.28619303 66.62769595 42.32069331 72.80018158 42.36830902 78.9728756 C42.38309137 81.32221891 42.3910392 83.67161596 42.39188385 86.02100563 C42.39426465 89.32405867 42.42143529 92.62608105 42.45410156 95.92895508 C42.4490712 96.88993607 42.44404083 97.85091705 42.43885803 98.84101868 C42.58409174 108.397113 45.17980892 117.37802929 51.984375 124.33984375 C59.83862499 130.808945 69.31798428 130.93597306 79.04980469 130.21875 C85.72169082 129.47037619 90.37420005 127.05313038 94.9375 122.1875 C99.86749091 115.94671151 102.09212483 109.33410941 102.15821838 101.3745575 C102.1680072 100.47578384 102.17779602 99.57701019 102.18788147 98.65100098 C102.19363693 97.67779907 102.1993924 96.70459717 102.20532227 95.7019043 C102.21522186 94.66729568 102.22512146 93.63268707 102.23532104 92.56672668 C102.26686704 89.15258052 102.29166626 85.73842045 102.31640625 82.32421875 C102.33698173 79.95481508 102.35797836 77.58541503 102.37937927 75.21601868 C102.43453856 68.98374365 102.48397497 62.75143583 102.53222656 56.519104 C102.58248642 50.15788865 102.63814908 43.79672084 102.69335938 37.43554688 C102.80086585 24.95707038 102.90182818 12.47855343 103 0 C116.86 0 130.72 0 145 0 C145.04528588 13.87420013 145.08193639 27.7483507 145.10362434 41.62260818 C145.1140364 48.06581633 145.1281484 54.50897104 145.15087891 60.95214844 C145.17269934 67.17670971 145.18458799 73.40121976 145.18975449 79.62581635 C145.19343376 81.99391231 145.20061825 84.36200565 145.21146011 86.73007965 C145.22609734 90.06132443 145.22797285 93.39236077 145.22705078 96.72363281 C145.23424133 97.69036926 145.24143188 98.65710571 145.24884033 99.65313721 C145.19498209 117.7779167 139.82586784 134.85117148 127.25 148.25 C110.51958476 163.95479592 88.87076304 168.78911942 66.6328125 168.21875 C46.87801189 167.42186413 29.88224514 160.04584062 16 146 C2.93833582 131.74398132 -0.18357808 113.93009051 -0.11352539 95.24780273 C-0.11367142 94.21261002 -0.11381744 93.1774173 -0.1139679 92.1108551 C-0.113276 88.71841269 -0.10551771 85.32602647 -0.09765625 81.93359375 C-0.0957895 79.56991099 -0.09436681 77.20622784 -0.09336853 74.84254456 C-0.08956361 68.6431673 -0.07975072 62.44381374 -0.06866455 56.2444458 C-0.05840678 49.90971192 -0.05386158 43.57497418 -0.04882812 37.24023438 C-0.03812654 24.82681087 -0.02054625 12.41341112 0 0 Z " fill="#C61618" transform="translate(149,12)"/>
        <path d="M0 0 C44.55 0 89.1 0 135 0 C135 11.55 135 23.1 135 35 C119.49 35 103.98 35 88 35 C88 77.57 88 120.14 88 164 C74.47 164 60.94 164 47 164 C47 121.43 47 78.86 47 35 C31.49 35 15.98 35 0 35 C0 23.45 0 11.9 0 0 Z " fill="#C61618" transform="translate(0,12)"/>
        <path d="M0 0 C12.65245636 9.55647932 22.33026625 23.10844992 25 39 C25.07747197 40.76552798 25.10799073 42.53358456 25.09765625 44.30078125 C25.09282227 45.76547852 25.09282227 45.76547852 25.08789062 47.25976562 C25.07532227 48.77086914 25.07532227 48.77086914 25.0625 50.3125 C25.05798828 51.33923828 25.05347656 52.36597656 25.04882812 53.42382812 C25.03708184 55.94927882 25.02065565 58.47460905 25 61 C21.14269541 62.2857682 17.50819118 62.13111459 13.48950195 62.11352539 C12.62099609 62.11367142 11.75249023 62.11381744 10.85766602 62.1139679 C7.98451243 62.11327076 5.11142352 62.10548761 2.23828125 62.09765625 C0.24716731 62.09579137 -1.74394708 62.09436779 -3.73506165 62.09336853 C-8.97772486 62.0895489 -14.22036041 62.07972332 -19.4630127 62.06866455 C-24.81192653 62.05843854 -30.16084483 62.05386835 -35.50976562 62.04882812 C-46.00652258 62.03810058 -56.50325899 62.02103077 -67 62 C-66.38195599 63.26841763 -65.76011494 64.5349855 -65.13671875 65.80078125 C-64.79084717 66.50630127 -64.44497559 67.21182129 -64.08862305 67.9387207 C-60.06259115 75.56190691 -53.92829122 79.03692021 -46.1953125 82.1171875 C-36.47768183 84.80200966 -24.83858425 83.97170364 -16 79 C-14.77977206 77.88908414 -13.58959262 76.74392832 -12.4375 75.5625 C-9.6388916 72.99873986 -9.6388916 72.99873986 -7.01953125 73.00390625 C-4.21102784 73.77249841 -1.67390229 74.83701358 1 76 C2.62152198 76.67008727 4.2440054 77.33785041 5.8671875 78.00390625 C10.59709656 79.95925313 15.30358764 81.96565938 20 84 C16.36371638 94.37146906 6.32999884 100.14257585 -3 105 C-21.62834089 112.98935358 -39.78840466 114.53275647 -59 108 C-75.66757696 101.00557038 -86.3582453 88.4505172 -93.7734375 72.3359375 C-99.57362761 56.56089817 -98.49086556 39.28134427 -91.6796875 24.046875 C-84.03212868 9.08607687 -72.06679165 -2.49323673 -56 -8 C-36.43258977 -13.64620365 -16.98636416 -11.5310457 0 0 Z M-62 28 C-65.40529104 32.11254641 -65.40529104 32.11254641 -67 37 C-46.54 37 -26.08 37 -5 37 C-8.34994238 28.62514404 -13.93082823 23.00217957 -22 19 C-36.22387449 13.02597272 -51.38269117 17.59169332 -62 28 Z " fill="#C61618" transform="translate(475,68)"/>
        <path d="M0 0 C1.25159912 0.00523682 2.50319824 0.01047363 3.79272461 0.01586914 C4.78942421 0.01799156 4.78942421 0.01799156 5.80625916 0.02015686 C7.93590735 0.02577021 10.06545175 0.03832485 12.19506836 0.05102539 C13.63582205 0.05603868 15.07657739 0.06060188 16.51733398 0.06469727 C20.05577938 0.07574394 23.59416375 0.09301747 27.13256836 0.11352539 C24.45912631 8.63809504 21.07225691 16.85114972 17.69506836 25.11352539 C17.0372097 26.72883083 16.37958289 28.34423071 15.72216797 29.9597168 C13.91606143 34.3956075 12.10619711 38.82995657 10.2956543 43.26403809 C8.695891 47.18335741 7.09840977 51.10360545 5.50083923 55.02381897 C-2.86639287 75.55469948 -11.25514589 96.07665222 -19.68029785 116.58383179 C-26.96622109 134.32071611 -34.19415573 152.08121329 -41.41967773 169.84277344 C-41.87622238 170.96453979 -42.33276703 172.08630615 -42.80314636 173.24206543 C-43.65425574 175.33336107 -44.50496799 177.4248184 -45.35517883 179.51647949 C-48.1562341 186.39820033 -51.00951442 193.25452407 -53.86743164 200.11352539 C-64.09743164 200.11352539 -74.32743164 200.11352539 -84.86743164 200.11352539 C-82.61751699 193.36378145 -82.61751699 193.36378145 -81.27368164 190.09155273 C-80.97082245 189.35131363 -80.66796326 188.61107452 -80.35592651 187.84840393 C-80.02972321 187.05675339 -79.7035199 186.26510284 -79.36743164 185.44946289 C-79.02003937 184.60185898 -78.67264709 183.75425507 -78.31472778 182.88096619 C-77.16741676 180.08274883 -76.01739471 177.28565378 -74.86743164 174.48852539 C-74.05455921 172.5070847 -73.24190011 170.52555648 -72.42944336 168.54394531 C-70.74262266 164.43023658 -69.05488646 160.31690532 -67.36645508 156.20385742 C-63.93459186 147.84222673 -60.51217335 139.47673654 -57.09057617 131.11090088 C-55.98123198 128.39864311 -54.87161679 125.68649631 -53.76196289 122.97436523 C-48.12292411 109.19048925 -42.49402395 95.40248592 -36.86743164 81.61352539 C-30.61763583 66.29780942 -24.36539203 50.98310028 -18.10400391 35.67211914 C-17.33335889 33.78757238 -16.56284671 31.90297129 -15.79248047 30.01831055 C-13.77524569 25.08352102 -11.75575229 20.14967425 -9.73101807 15.21795654 C-9.17145291 13.85437983 -8.61260985 12.49050648 -8.05462646 11.12628174 C-7.34754419 9.39836819 -6.63693246 7.67190009 -5.92602539 5.94555664 C-5.54631592 5.02105713 -5.16660645 4.09655762 -4.77539062 3.14404297 C-3.43023888 0.13580767 -3.43023888 0.13580767 0 0 Z " fill="#C61618" transform="translate(372.867431640625,-0.113525390625)"/>
        </svg>
        """
        # Create pixmap scaled to fit (and avoid clipping)
        logo_pixmap = svg_to_pixmap(SVG_LOGO, max_width=100, max_height=20) # tweak these if needed
        logo_label = QLabel()
        logo_label.setPixmap(logo_pixmap)
        logo_label.setFixedSize(logo_pixmap.size()) # ensure layout doesn't shrink it
        logo_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        logo_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        title_row.addWidget(logo_label, 0, Qt.AlignRight)
        main_layout.addLayout(title_row)

        subtitle_label = QLabel("Select an application to launch:")
        subtitle_label.setObjectName("SubtitleLabel")
        main_layout.addWidget(subtitle_label)

        main_layout.addSpacing(10)

        # Launch Buttons
        for app_id, (text, svg, handler) in self.APP_IDS.items():
            btn = self._create_launch_button(app_id, text, svg, handler)
            self.buttons[app_id] = btn
            main_layout.addWidget(btn)

        main_layout.addSpacing(20)

        # --- Active Apps Section (NEW) ---
        self._create_active_apps_section(main_layout)

        main_layout.addStretch()

        # Footer (Unchanged)
        author_label = QLabel("<i>4CBLA00 at TU/e<br />Written by Csaba Benedek</i>")
        author_label.setAlignment(Qt.AlignCenter)
        author_label.setTextFormat(Qt.RichText)
        author_label.setObjectName("SubtitleLabel")
        main_layout.addWidget(author_label)
        
        exit_button = QPushButton("Exit")
        exit_button.setStyleSheet("background-color: #c0392b; border: none; padding: 10px; border-radius: 10px;")
        exit_button.clicked.connect(self.close)
        main_layout.addWidget(exit_button)
        
        self.setLayout(main_layout)

    def _create_active_apps_section(self, layout):
        """Creates the label and QListWidget for active applications."""
        active_label = QLabel("Currently Active Applications:")
        active_label.setObjectName("SubtitleLabel")
        active_label.setStyleSheet("color: #ffffff; font-weight: bold;")
        layout.addWidget(active_label)

        self.active_list = QListWidget()
        self.active_list.setMaximumHeight(100) # Limit size
        self.active_list.setSelectionMode(QListWidget.NoSelection) # Prevent selection
        layout.addWidget(self.active_list)
        
    def _create_launch_button(self, app_id, text, svg_icon, handler):
        """Creates a launch button and stores it."""
        button = QPushButton()
        # Bind a lambda to pass the app_id to the handler
        button.clicked.connect(lambda: handler(app_id)) 
        
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
        
    def _launch_app(self, app_id, app_module_main_func):
        """Generic function to launch an app, disable the button, and update the list."""
        if app_id in self.active_apps:
            print(f"Error: {app_id} is already running.")
            return

        app_name, _, _ = self.APP_IDS[app_id]
        
        # 1. Launch App
        app_window = app_module_main_func() 
        
        # 2. Add to Active Apps List
        list_item = QListWidgetItem(app_name)
        self.active_list.addItem(list_item)
        
        # 3. Disable Launcher Button
        button = self.buttons[app_id]
        button.setEnabled(False)
        
        # 4. Store references and connect close event
        self.active_apps[app_id] = (app_window, button, list_item)
        
        # Connect the launched app's close event to a cleanup function
        # This is the crucial step to re-enable the button when the app is closed.
        # We use a lambda to pass the app_id to the cleanup function.
        app_window.installEventFilter(self) # We'll use eventFilter instead of overriding closeEvent
        app_window.destroyed.connect(lambda: self.clean_up_app(app_id))

        # 5. Show window
        app_window.show()
        print(f"Launching {app_name}...")

    def clean_up_app(self, app_id):
        """Re-enables the button and removes the item from the active list."""
        if app_id in self.active_apps:
            print(f"Cleaning up {self.APP_IDS[app_id][0]}...")
            app_window, button, list_item = self.active_apps[app_id]
            
            # 1. Re-enable button
            button.setEnabled(True)
            
            # 2. Remove from active list
            row = self.active_list.row(list_item)
            if row != -1:
                self.active_list.takeItem(row)
            
            # 3. Remove from internal tracking
            del self.active_apps[app_id]

    # --- Launch Handlers (Modified to call _launch_app) ---
    def launch_editor(self, app_id):
        self._launch_app(app_id, editor_main)

    def launch_optimizer(self, app_id):
        self._launch_app(app_id, optimizer_main)
        
    def launch_visualizer(self, app_id):
        self._launch_app(app_id, visualizer_main)

    # --- Window Management (Modified) ---
    
    def mousePressEvent(self, event):
        self.oldPos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        delta = QPoint(event.globalPosition().toPoint() - self.oldPos)
        self.move(self.pos() + delta)
        self.oldPos = event.globalPosition().toPoint()
        
    def closeEvent(self, event):
        """When the launcher closes, close all active sub-apps."""
        # Make a copy of keys because the dictionary will be modified during iteration
        for app_id in list(self.active_apps.keys()):
            app_window, _, _ = self.active_apps[app_id]
            if app_window.isVisible():
                app_window.close()
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