# ui/components/input.py - 设计系统单行输入，样式由 mymain.qss + 令牌驱动
from PySide6.QtWidgets import QLineEdit


class Input(QLineEdit):
    """可复用单行输入框，通过 objectName=DesignInput 由 QSS 驱动样式。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DesignInput")
