# ui/components/button.py - 设计系统按钮，样式由 mymain.qss + 令牌驱动
from PySide6.QtWidgets import QPushButton


class Button(QPushButton):
    """可复用按钮，通过 objectName=DesignButton 与 variant 由 QSS 驱动样式。"""

    def __init__(
        self,
        text: str = "",
        variant: str = "default",
        parent=None,
    ):
        super().__init__(text, parent)
        self.setObjectName("DesignButton")
        self.setProperty("variant", variant)
