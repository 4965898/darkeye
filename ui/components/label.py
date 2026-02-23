# ui/components/label.py - 设计系统标签，样式由 mymain.qss + 令牌驱动
from PySide6.QtWidgets import QLabel


class Label(QLabel):
    """可复用标签，通过 objectName=DesignLabel 由 QSS 驱动样式。"""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setObjectName("DesignLabel")
