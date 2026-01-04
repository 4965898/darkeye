from PySide6.QtWidgets import QPushButton, QHBoxLayout, QLabel,QVBoxLayout,QTextEdit,QDialog,QFileDialog,QGridLayout,QWidget,QFormLayout
from PySide6.QtGui import QIcon
from PySide6.QtCore import Slot,Qt
import logging
from config import APP_VERSION


class FirstPage(QWidget):
    '''这个是首页'''
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()


        githubLabel = QLabel()
        githubLabel.setText(
            '<a href="https://github.com/de4321/darkeye">https://github.com/de4321/darkeye</a>'
        )
        githubLabel.setTextFormat(Qt.RichText)
        githubLabel.setTextInteractionFlags(Qt.TextBrowserInteraction)
        githubLabel.setOpenExternalLinks(True)   # 关键

        form_layout.addRow(QLabel("欢迎使用暗之眼软件！"))
        form_layout.addRow(QLabel("软件本体版本"),QLabel(APP_VERSION))
        form_layout.addRow(QLabel("GitHub地址"),githubLabel)
        layout.addLayout(form_layout)