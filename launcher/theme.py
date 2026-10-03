"""Launcher presentation: shared palettes and resolution-independent icons."""
import math
import os
from pathlib import Path

from .qt import QColor, QIcon, QPainter, QPainterPath, QPalette, QPen, QPixmap, QPointF, QRectF, Qt


STATE_COLORS = {"pass": "#00864a", "warn": "#686b75", "error": "#b24e4e"}
DARK_STATE_COLORS = {"pass": "#71c797", "warn": "#a5a6af", "error": "#df9999"}

LIGHT_COLORS = {
    "page": "#ffffff", "surface": "#ffffff", "body": "#f4f4f6",
    "text": "#282a30", "muted": "#686b75", "subtle": "#858892", "border": "#e1e2e6",
    "outline": "#dcdde2", "line": "#e8e9ec", "button_text": "#525660",
    "hover": "#eeeef1", "hover_border": "#bfc3c9", "pressed": "#e5e7eb",
    "disabled_text": "#a4a6ae", "disabled": "#f0f0f2", "header": "#eeeff2",
    "nav_text": "#60646e", "icon": "#737783", "accent_text": STATE_COLORS["pass"],
    "accent_soft": "#e8f3ed", "step": "#e4f0e9", "accent_border": "#d5e9dd",
    "selection": "#cfe8da", "primary_disabled": "#d7e9df", "primary_disabled_text": "#829c8e",
    "error_text": STATE_COLORS["error"], "error_soft": "#f7eaea", "danger": "#fff5f5",
    "danger_border": "#ead1d1", "danger_hover": "#f8e7e7", "danger_hover_border": "#d4a6a6",
    "danger_pressed": "#f0dada", "scroll": "#cfd1d6", "scroll_hover": "#b9bdc5",
}
DARK_COLORS = {
    "page": "#101012", "surface": "#19191c", "body": "#262629",
    "text": "#eeeeF0", "muted": "#a5a6af", "subtle": "#85858e", "border": "#303034",
    "outline": "#3a3a40", "line": "#303034", "button_text": "#d1d1d7",
    "hover": "#333338", "hover_border": "#505057", "pressed": "#3c3c42",
    "disabled_text": "#71717c", "disabled": "#252528", "header": "#262629",
    "nav_text": "#b5b5be", "icon": "#b5b5be", "accent_text": DARK_STATE_COLORS["pass"],
    "accent_soft": "#20372a", "step": "#20372a", "accent_border": "#31513d",
    "selection": "#31513d", "primary_disabled": "#263a2d", "primary_disabled_text": "#789382",
    "error_text": DARK_STATE_COLORS["error"], "error_soft": "#382729", "danger": "#2d2225",
    "danger_border": "#5d3b3f", "danger_hover": "#3e292d", "danger_hover_border": "#86565c",
    "danger_pressed": "#4d3035", "scroll": "#49494f", "scroll_hover": "#606068",
}

_STYLE = """
QMainWindow, QWidget#shell, QWidget#page { background: @page@; }
QWidget { color: @text@; font-family: 'Microsoft YaHei UI'; font-size: 13px; }
QFrame#sidebar { background: @surface@; border-right: 1px solid @border@; }
QLabel#brandMark { background: transparent; border: none; }
QLabel#brand { font-size: 15px; font-weight: 700; }
QLabel#eyebrow { color: @subtle@; font-size: 10px; font-weight: 500; letter-spacing: 1px; }
QLabel#title { font-size: 24px; font-weight: 600; }
QLabel#heroTitle { font-size: 22px; font-weight: 600; color: @text@; }
QLabel#subtitle, QLabel#muted { color: @muted@; }
QLabel#cardTitle { font-size: 16px; font-weight: 600; }
QLabel#cardHeader { background: @surface@; border-bottom: 1px solid @border@; border-top-left-radius: 12px; border-top-right-radius: 12px; padding: 15px 18px; font-size: 16px; font-weight: 600; }
QLabel#metric { font-size: 26px; font-weight: 700; }
QLabel#stepNumber { color: @accent_text@; background: @step@; border-radius: 8px; font-size: 14px; font-weight: 600; }
QLabel#badge { color: @accent_text@; background: @accent_soft@; padding: 5px 10px; border-radius: 7px; font-size: 11px; }
QLabel#badge[state="error"] { color: @error_text@; background: @error_soft@; }
QLabel#badge[state="warn"] { color: @muted@; background: @header@; }
QFrame#card { background: @surface@; border: 1px solid @border@; border-radius: 12px; }
QFrame#cardBody { background: @body@; border-bottom-left-radius: 12px; border-bottom-right-radius: 12px; }
QFrame#hero { background: @body@; border: 1px solid @border@; border-radius: 12px; }
QFrame#sidebarNote { background: @body@; border: 1px solid @border@; border-radius: 10px; }
QFrame#portList { background: @surface@; border: 1px solid @outline@; border-radius: 12px; }
QPushButton { background: @surface@; color: @button_text@; border: 1px solid @outline@; border-radius: 7px; padding: 9px 13px; font-weight: 500; }
QPushButton:hover { background: @hover@; border-color: @hover_border@; }
QPushButton:pressed { background: @pressed@; }
QPushButton:focus { border-color: #008c4a; }
QPushButton:disabled { color: @disabled_text@; background: @disabled@; border-color: @border@; }
QPushButton#primary { background: #008c4a; color: #ffffff; border: 1px solid #008c4a; font-weight: 600; }
QPushButton#primary:hover { background: #007d42; border-color: #007d42; }
QPushButton#primary:pressed { background: #006b39; }
QPushButton#primary:disabled { background: @primary_disabled@; color: @primary_disabled_text@; border-color: @primary_disabled@; }
QPushButton#danger { background: @danger@; color: @error_text@; border: 1px solid @danger_border@; padding: 8px 10px; }
QPushButton#danger:hover { background: @danger_hover@; border-color: @danger_hover_border@; }
QPushButton#danger:pressed { background: @danger_pressed@; }
QPushButton#danger:disabled { background: @disabled@; color: @disabled_text@; border-color: @border@; }
QPushButton#nav { background: transparent; border: 1px solid transparent; text-align: left; padding: 13px 14px; color: @nav_text@; }
QPushButton#nav:hover { background: @body@; color: @text@; }
QPushButton#nav:checked { background: @accent_soft@; color: @accent_text@; border: 1px solid @accent_border@; font-weight: 600; }
QPushButton#nav:focus { border-color: #008c4a; }
QPushButton#headerAction { background: transparent; border: 1px solid transparent; border-radius: 6px; padding: 4px; }
QPushButton#headerAction:hover { background: @hover@; }
QPushButton#headerAction:pressed { background: @pressed@; }
QPushButton#headerAction:focus { border-color: #008c4a; }
QPushButton#headerAction:disabled { background: transparent; border-color: transparent; }
QLineEdit, QSpinBox, QPlainTextEdit, QTextBrowser, QComboBox { background: @surface@; border: 1px solid @outline@; border-radius: 7px; padding: 10px; selection-background-color: @selection@; selection-color: @text@; }
QLineEdit:focus, QSpinBox:focus, QPlainTextEdit:focus { border-color: #008c4a; }
QLineEdit, QSpinBox { min-height: 20px; }
QPlainTextEdit#log { font-family: 'Cascadia Mono', 'Consolas', 'Microsoft YaHei UI'; font-size: 12px; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView { background: @surface@; color: @text@; border: 1px solid @outline@; selection-background-color: @accent_soft@; selection-color: @text@; }
QCheckBox { spacing: 8px; }
QTableWidget { background: @surface@; alternate-background-color: @surface@; border: 1px solid @border@; border-radius: 8px; gridline-color: @line@; }
QTableWidget#portTable { background: @surface@; border: none; border-radius: 0; }
QTableWidget#portTable QHeaderView::section { background: @surface@; border-bottom: 1px solid @border@; }
QTableWidget::item { padding: 8px; border-bottom: 1px solid @line@; }
QHeaderView::section { background: @header@; color: @nav_text@; border: none; padding: 10px 8px; font-size: 12px; font-weight: 600; }
QTableCornerButton::section { background: @header@; border: none; }
QScrollArea { background: transparent; border: none; }
QScrollArea > QWidget > QWidget { background: @page@; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 3px 0; }
QScrollBar::handle:vertical { background: @scroll@; border-radius: 4px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: @scroll_hover@; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QScrollBar:horizontal { background: transparent; height: 8px; }
QScrollBar::handle:horizontal { background: @scroll@; border-radius: 4px; min-width: 32px; }
QScrollBar::handle:horizontal:hover { background: @scroll_hover@; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
QToolTip { background: @surface@; color: @text@; border: 1px solid @outline@; padding: 6px; }
QMessageBox, QFileDialog, QMenu { background: @surface@; }
QMenu { border: 1px solid @outline@; }
QMenu::item { padding: 8px 16px; }
QMenu::item:selected { background: @accent_soft@; }
"""


def colors(dark=False):
    return DARK_COLORS if dark else LIGHT_COLORS


def state_colors(dark=False):
    return DARK_STATE_COLORS if dark else STATE_COLORS


def style_sheet(dark=False):
    value = _STYLE
    for name, color in colors(dark).items():
        value = value.replace(f"@{name}@", color)
    return value


STYLE = style_sheet()


def application_icon():
    return QIcon(str(Path(__file__).with_name("favicon.ico")))


def brand_pixmap():
    """Render the supplied sidebar image with the existing size and rounded corners."""
    source = QPixmap(str(Path(__file__).with_name("图标.png")))
    pixmap = QPixmap(84, 84)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    bounds = QRectF(0, 0, 84, 84)
    clip = QPainterPath()
    clip.addRoundedRect(bounds, 18, 18)
    painter.setClipPath(clip)
    side = min(source.width(), source.height())
    crop = QRectF((source.width() - side) / 2, (source.height() - side) / 2, side, side)
    painter.drawPixmap(bounds, source, crop)
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return pixmap


def set_application_identity():
    """Give the Windows taskbar a launcher identity rather than the Python host's."""
    if os.name != "nt":
        return
    import ctypes
    try:
        function = ctypes.WinDLL("shell32").SetCurrentProcessExplicitAppUserModelID
        function.argtypes = [ctypes.c_wchar_p]
        function.restype = ctypes.c_long
        function("MasterofGarden.Launcher")
    except (OSError, AttributeError):
        pass


def palette(dark=False):
    theme = colors(dark)
    value = QPalette()
    for role, color in {
        "Window": "page", "WindowText": "text", "Base": "surface", "AlternateBase": "body",
        "ToolTipBase": "surface", "ToolTipText": "text", "Text": "text", "Button": "surface",
        "ButtonText": "button_text", "BrightText": "text", "Highlight": "selection",
        "HighlightedText": "text", "PlaceholderText": "subtle",
        "Light": "hover", "Midlight": "body", "Mid": "border", "Dark": "outline", "Shadow": "page",
    }.items():
        value.setColor(getattr(QPalette.ColorRole, role), QColor(theme[color]))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        value.setColor(QPalette.ColorGroup.Disabled, role, QColor(theme["disabled_text"]))
    return value


def set_dark_titlebar(window, dark=False):
    """Match this window's native Windows titlebar when DWM supports it."""
    if os.name != "nt":
        return
    import ctypes
    from ctypes import wintypes
    try:
        function = ctypes.WinDLL("dwmapi").DwmSetWindowAttribute
        function.argtypes = [wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD]
        function.restype = ctypes.c_long
        enabled = wintypes.BOOL(dark)
        handle = int(window.winId())
        if function(handle, 20, ctypes.byref(enabled), ctypes.sizeof(enabled)) != 0:
            function(handle, 19, ctypes.byref(enabled), ctypes.sizeof(enabled))
    except (OSError, AttributeError):
        pass


def navigation_icon(index, active=False, dark=False):
    """Draw at 2x so the sidebar icons stay crisp on scaled displays."""
    pixmap = QPixmap(40, 40)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(2, 2)
    theme = colors(dark)
    painter.setPen(QPen(QColor(theme["accent_text"] if active else theme["icon"]), 1.5))
    if index == 0:
        painter.drawEllipse(QRectF(3, 3, 14, 14))
        painter.drawLine(QPointF(7, 13), QPointF(10, 6))
        painter.drawLine(QPointF(10, 6), QPointF(13, 13))
        painter.drawLine(QPointF(7, 13), QPointF(13, 13))
    elif index == 1:
        for x, y in ((3, 3), (12, 3), (3, 12), (12, 12)):
            painter.drawRoundedRect(QRectF(x, y, 5, 5), 1, 1)
    elif index == 2:
        painter.drawRoundedRect(QRectF(2, 3, 16, 14), 3, 3)
        points = ((4, 11), (7, 11), (9, 7), (12, 14), (14, 10), (16, 10))
        for start, end in zip(points, points[1:]):
            painter.drawLine(QPointF(*start), QPointF(*end))
    elif index == 3:
        for y, x in ((5, 12), (10, 7), (15, 12)):
            painter.drawLine(QPointF(3, y), QPointF(17, y))
            painter.setBrush(QColor(theme["accent_soft"] if active else theme["surface"]))
            painter.drawEllipse(QPointF(x, y), 2, 2)
    else:
        painter.drawEllipse(QRectF(3, 3, 14, 14))
        painter.drawPoint(QPointF(10, 6.5))
        painter.drawLine(QPointF(10, 9), QPointF(10, 14))
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)


def header_icon(kind, dark=False):
    pixmap = QPixmap(40, 40)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.scale(2, 2)
    theme = colors(dark)
    painter.setPen(QPen(QColor(theme["disabled_text"] if kind == "gm" else theme["icon"]), 1.5))
    if kind == "gm":
        for x, y in ((3, 3), (12, 3), (3, 12), (12, 12)):
            painter.drawRoundedRect(QRectF(x, y, 5, 5), 1, 1)
    elif kind == "moon":
        outer, inner = QPainterPath(), QPainterPath()
        outer.addEllipse(QRectF(3, 3, 14, 14))
        inner.addEllipse(QRectF(7, 0, 14, 14))
        painter.drawPath(outer.subtracted(inner))
    elif kind == "sun":
        painter.drawEllipse(QRectF(6, 6, 8, 8))
        for index in range(8):
            angle = index * math.pi / 4
            painter.drawLine(QPointF(10 + 6 * math.cos(angle), 10 + 6 * math.sin(angle)),
                             QPointF(10 + 9 * math.cos(angle), 10 + 9 * math.sin(angle)))
    elif kind == "settings":
        path = QPainterPath()
        for index in range(32):
            radius = (6.5, 8, 8, 6.5)[index % 4]
            angle = index * math.pi / 16
            point = QPointF(10 + radius * math.cos(angle), 10 + radius * math.sin(angle))
            if index == 0:
                path.moveTo(point)
            else:
                path.lineTo(point)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawEllipse(QRectF(7, 7, 6, 6))
    painter.end()
    pixmap.setDevicePixelRatio(2)
    return QIcon(pixmap)
