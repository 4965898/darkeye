
from PySide6.QtWidgets import QLabel, QVBoxLayout
from PySide6.QtCore import Qt
import logging
from ui.base import LazyWidget



class ForceDirectPage(LazyWidget):
    def __init__(self):
        super().__init__()


    def _lazy_load(self):
        logging.info("----------力导向图界面----------")

        
        from core.graph.ForceDirectedViewWidget import ForceDirectedViewWidget


        mainlayout = QVBoxLayout()
        self.setLayout(mainlayout)
        mainlayout.setContentsMargins(0, 0, 0, 0)

        placeholder = QLabel("正在生成力导向图...")
        placeholder.setAlignment(Qt.AlignCenter)# type: ignore[arg-type]
        mainlayout.addWidget(placeholder)


        view = ForceDirectedViewWidget()

        mainlayout.removeWidget(placeholder)
        placeholder.deleteLater()
        mainlayout.addWidget(view)
        view.session.reload()


