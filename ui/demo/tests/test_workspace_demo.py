"""独立启动工作区 Demo 窗口，用于验证窗格、拆分、拖拽、预览功能。"""
import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parents[3]  
sys.path.insert(0, str(root_dir))

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
)
from PySide6.QtCore import Qt, QEvent, QObject
from PySide6.QtGui import QIcon

from ui.demo.workspace_manager import WorkspaceManager, Placement, ContentConfig
from ui.demo.layout_tree import LayoutTree
from ui.demo.pane_widget import PaneWidget
from config import ICONS_PATH


"""工作区 Demo 主入口：WorkspaceDemoWidget，组合 Pane、LayoutTree、拖拽与预览。"""






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
        #pane7 = self._manager.split(pane3, Placement.Top, ratio=0.5)#可以不填东西


        self._manager.fill_pane(root, d_a)
        self._manager.fill_pane(root, d_b)
        self._manager.fill_pane(root, d_c)
        #self._manager.fill_pane(root, d_d)

        self._manager.fill_pane(pane3, d3)
        self._manager.fill_pane(pane4, d4)
        self._manager.fill_pane(pane5, d5)
        self._manager.fill_pane(pane5, d_e)

    def layout_tree(self) -> LayoutTree:
        return self._manager.layout_tree()




def _pane_under_cursor(tree: LayoutTree, global_pos):
    """从点击位置向上查找属于 tree 的 PaneWidget。"""
    w = QApplication.widgetAt(global_pos)
    while w:
        if isinstance(w, PaneWidget) and tree.find_parent_of_pane(w) is not None:
            return w
        w = w.parent() if hasattr(w, "parent") else None
    return None


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = QMainWindow()
    win.setWindowTitle("工作区 Demo")

    workspace = WorkspaceDemoWidget()
    tree = workspace.layout_tree()
    panes = tree.panes()
    split_target_holder = [panes[0]] if panes else [None]

    def update_target_label():
        target = split_target_holder[0]
        current_target_label.setText(
            "当前拆分目标: " + (target.pane_id if target else "无")
        )

    class PaneSelectFilter(QObject):
        """点击窗格时将其设为当前拆分目标。"""

        def eventFilter(self, obj, event):
            if (
                event.type() == QEvent.MouseButtonPress
                and event.button() == Qt.LeftButton
            ):
                pos = (
                    event.globalPosition().toPoint()
                    if hasattr(event, "globalPosition")
                    else event.globalPos()
                )
                pane = _pane_under_cursor(tree, pos)
                if pane is not None:
                    split_target_holder[0] = pane
                    update_target_label()
            return False

    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(4, 4, 4, 4)

    current_target_label = QLabel(
        "当前拆分目标: " + (split_target_holder[0].pane_id if split_target_holder[0] else "无")
    )
    layout.addWidget(current_target_label)

    _pane_select_filter = PaneSelectFilter(container)
    container.installEventFilter(_pane_select_filter)

    def add_pane_right():
        target = split_target_holder[0]
        if target is None:
            return
        new_pane = workspace._manager.split(target, Placement.Right)
        split_target_holder[0] = new_pane
        update_target_label()

    def add_pane_left():
        target = split_target_holder[0]
        if target is None:
            return
        new_pane = workspace._manager.split(target, Placement.Left)
        split_target_holder[0] = new_pane
        update_target_label()

    def add_pane_above():
        target = split_target_holder[0]
        if target is None:
            return
        new_pane = workspace._manager.split(target, Placement.Top)
        split_target_holder[0] = new_pane
        update_target_label()

    def add_pane_below():
        target = split_target_holder[0]
        if target is None:
            return
        new_pane = workspace._manager.split(target, Placement.Bottom)
        split_target_holder[0] = new_pane
        update_target_label()

    btn_row = QHBoxLayout()
    btn_row.addWidget(QLabel("以当前选中窗格为节点："))

    btn_right = QPushButton("右侧添加窗格 (水平拆分)")
    btn_right.clicked.connect(add_pane_right)
    btn_row.addWidget(btn_right)

    btn_left = QPushButton("左侧添加窗格 (水平拆分)")
    btn_left.clicked.connect(add_pane_left)
    btn_row.addWidget(btn_left)

    btn_top = QPushButton("上方添加窗格 (垂直拆分)")
    btn_top.clicked.connect(add_pane_above)
    btn_row.addWidget(btn_top)

    btn_below = QPushButton("下方添加窗格 (垂直拆分)")
    btn_below.clicked.connect(add_pane_below)
    btn_row.addWidget(btn_below)

    btn_print = QPushButton("打印树数据")
    btn_print.clicked.connect(lambda: workspace.layout_tree().print_tree())
    btn_row.addWidget(btn_print)
    btn_row.addStretch()
    layout.addLayout(btn_row)

    layout.addWidget(workspace, 1)

    win.setCentralWidget(container)
    win.resize(900, 600)
    win.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
