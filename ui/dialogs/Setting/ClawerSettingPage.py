from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel,QVBoxLayout,QTextEdit,QDialog,QFileDialog,QGridLayout,QWidget
from PySide6.QtGui import QIcon
from PySide6.QtCore import Slot
import logging
from pathlib import Path
from ui.basic import MultiplePathManagement


class ClawerSettingPage(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("<h3>爬虫相关设置</h3>"))