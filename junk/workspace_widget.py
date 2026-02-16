"""工作区 Demo 主入口：WorkspaceDemoWidget，组合 Pane、LayoutTree、拖拽与预览。"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtGui import QIcon

from config import ICONS_PATH
from ui.demo.layout_tree import LayoutTree
from ui.demo.workspace_manager import WorkspaceManager, Placement, ContentConfig


def _make_placeholder_content(text: str) -> QWidget:
    """创建占位内容。"""
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.addWidget(QLabel(text))
    return w


class WorkspaceDemoWidget(QWidget):
    """工作区 Demo 根容器：委托 WorkspaceManager，支持动态拆分与空窗格自毁。"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._manager = WorkspaceManager(self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._manager.widget())

        root = self._manager.get_root_pane()

        def make_config(title: str, icon_name: str) -> ContentConfig:
            d = self._manager.create_content_config()
            d.set_window_title(title).set_icon(QIcon(str(ICONS_PATH / icon_name))).set_widget(_make_placeholder_content(title))
            return d

        d_a = make_config("内容 A", "library-big.svg")
        d_b = make_config("内容 B", "film.svg")
        d_c = make_config("内容 C", "chart-line.svg")
        d_d = make_config("内容 D", "scroll-text.svg")
        d_e = make_config("内容 E", "layout-panel-left.svg")

        d3 = make_config("内容 A", "library-big.svg")
        d4 = make_config("内容 B", "film.svg")
        d5 = make_config("内容 A 下", "layout-panel-left.svg")

        # 先搭架子再填充：layout_tree 在 reparent 后会做 updateGeometry/update，两种顺序均支持
        pane3 = self._manager.split(root, Placement.Right, ratio=0.3)
        pane4 = self._manager.split(root, Placement.Bottom, ratio=0.4)
        pane5 = self._manager.split(pane3, Placement.Bottom, ratio=0.5)
        pane6 = self._manager.split(pane5, Placement.Left, ratio=0.5)
        pane7 = self._manager.split(pane3, Placement.Top, ratio=0.5)


        self._manager.fill_pane(root, d_a)
        self._manager.fill_pane(root, d_b)
        self._manager.fill_pane(root, d_c)
        self._manager.fill_pane(root, d_d)

        self._manager.fill_pane(pane3, d3)
        self._manager.fill_pane(pane4, d4)
        self._manager.fill_pane(pane5, d5)
        self._manager.fill_pane(pane5, d_e)

    def layout_tree(self) -> LayoutTree:
        return self._manager.layout_tree()
