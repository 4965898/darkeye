from PySide6.QtWidgets import QWidget, QVBoxLayout

from ui.widgets.ShelfWidget import ShelfWidget


class ShelfDemoPage(QWidget):
    """
    拟物化书架 Demo 页面（组合 ShelfWidget）
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(ShelfWidget(self))
