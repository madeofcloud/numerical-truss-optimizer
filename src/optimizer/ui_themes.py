# ui_themes.py

LIGHT_THEME = """
QMainWindow, QWidget {
    background-color: #f7f7f7;
    color: #222;
}
QFrame {
    background-color: #fafafa;
    border: 1px solid #d0d0d0;
    border-radius: 6px;
}
QLabel {
    color: #222;
}
QPushButton {
    background-color: #e6e6e6;
    border: 1px solid #c0c0c0;
    border-radius: 6px;
    padding: 6px 12px;
}
QPushButton:hover {
    background-color: #d0d0d0;
}
QLineEdit, QTableWidget {
    background-color: #ffffff;
    border: 1px solid #bfbfbf;
    border-radius: 4px;
    selection-background-color: #c72125; /* UPDATED from #d0e7ff */
    selection-color: white; /* UPDATED from black for contrast */
    gridline-color: #d9d9d9;
}
QHeaderView::section {
    background-color: #f1f1f1;
    color: #222;
    padding: 6px;
    font-weight: bold;
    border: 0px;
    border-bottom: 1px solid #d0d0d0;
}
QHeaderView::section:horizontal {
    border-right: 1px solid #d0d0d0;
}
QHeaderView::section:vertical {
    border-bottom: 1px solid #d0d0d0;
}
QTableCornerButton::section {
    background-color: #f1f1f1;
    border: none;
}
QTabWidget::pane {
    border: 1px solid #aaa;
    background: #ffffff;
}
QTabBar::tab {
    background: #f1f1f1;
    border: 1px solid #ccc;
    padding: 6px 12px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background: #ffffff;
    border-bottom-color: #ffffff;
}
QTableWidget::item:selected { /* Enhanced selection visibility */
    background-color: #c72125; /* Brighter background */
}
QSlider::groove:horizontal {
    border: 1px solid #bbb;
    height: 6px;
    background: #ddd;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #c72125; /* UPDATED from #5b9bd5 */
    border: 1px solid #c72125; /* UPDATED from #5b9bd5 */
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
"""

DARK_THEME = """
QMainWindow, QWidget {
    background-color: #2b2b2b;
    color: #f0f0f0;
}
QFrame {
    background-color: #323232;
    border: 1px solid #4a4a4a;
    border-radius: 6px;
}
QLabel {
    color: #f0f0f0;
}
QPushButton {
    background-color: #3c3f41;
    color: white;
    border: 1px solid #5b5b5b;
    border-radius: 6px;
    padding: 6px 12px;
}
QPushButton:hover {
    background-color: #505354;
}
QLineEdit, QTableWidget {
    background-color: #2f2f2f;
    color: #f0f0f0;
    border: 1px solid #5b5b5b;
    border-radius: 4px;
    selection-background-color: #c72125; /* UPDATED from #00bcd4 */
    selection-color: black;
    gridline-color: #3f3f3f;
}
QHeaderView::section {
    background-color: #3a3a3a;
    color: #f0f0f0;
    padding: 6px;
    font-weight: bold;
    border: 0px;
    border-bottom: 1px solid #4a4a4a;
}
QHeaderView::section:horizontal {
    border-right: 1px solid #4a4a4a;
}
QHeaderView::section:vertical {
    border-bottom: 1px solid #4a4a4a;
}
QTableCornerButton::section {
    background-color: #3a3a3a;
    border: none;
}
QTabWidget::pane {
    border: 1px solid #555;
    background: #2f2f2f;
}
QTabBar::tab {
    background: #3a3a3a;
    border: 1px solid #555;
    padding: 6px 12px;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background: #2f2f2f;
    border-bottom-color: #2f2f2f;
}
QSlider::groove:horizontal {
    border: 1px solid #555;
    height: 6px;
    background: #444;
    border-radius: 3px;
}
}
QTableWidget::item:selected { /* Enhanced selection visibility */
    background-color: #c72125; /* Brighter background */
}
QSlider::handle:horizontal {
    background: #c72125; /* UPDATED from #00bcd4 */
    border: 1px solid #c72125; /* UPDATED from #00bcd4 */
    width: 14px;
    margin: -5px 0;
    border-radius: 7px;
}
"""