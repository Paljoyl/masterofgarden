"""Use PySide6 with a compatible PyQt6 fallback."""
try:
    from PySide6.QtCore import Qt, QThread, QTimer, Signal, QLockFile, QRectF, QPointF, QSize, QUrl
    from PySide6.QtGui import QFont, QFontDatabase, QColor, QIcon, QPixmap, QPainter, QPainterPath, QPalette, QPen
    from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QStackedWidget, QFrame, QTableWidget, QTableWidgetItem,
        QHeaderView, QLineEdit, QSpinBox, QFileDialog, QPlainTextEdit, QMessageBox, QAbstractItemView,
        QScrollArea, QGridLayout, QSizePolicy, QComboBox, QCheckBox, QMenu, QStyledItemDelegate, QStyle,
        QDialog, QDialogButtonBox, QTextBrowser)
    BINDING = "PySide6"
except ImportError:
    from PyQt6.QtCore import Qt, QThread, QTimer, pyqtSignal as Signal, QLockFile, QRectF, QPointF, QSize, QUrl
    from PyQt6.QtGui import QFont, QFontDatabase, QColor, QIcon, QPixmap, QPainter, QPainterPath, QPalette, QPen
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QStackedWidget, QFrame, QTableWidget, QTableWidgetItem,
        QHeaderView, QLineEdit, QSpinBox, QFileDialog, QPlainTextEdit, QMessageBox, QAbstractItemView,
        QScrollArea, QGridLayout, QSizePolicy, QComboBox, QCheckBox, QMenu, QStyledItemDelegate, QStyle,
        QDialog, QDialogButtonBox, QTextBrowser)
    BINDING = "PyQt6（兼容模式）"
