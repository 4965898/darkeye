"""工作区管理类：持布局树、窗格工厂、拖拽与预览，供 WorkspaceDemoWidget 等容器使用。"""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon

from ui.demo.pane_widget import PaneWidget
from ui.demo.layout_tree import LayoutTree, SplitNode
from ui.demo.tab_drag_handler import create_drop_handler
from ui.demo.split_preview import SplitPreviewOverlay


# 与 QtAds 的 LeftDockWidgetArea / CenterDockWidgetArea 等语义一致，便于对照 test_dock 写法
class Placement:
    Left = 1
    Right = 2
    Top = 3
    Bottom = 4


def _make_placeholder_content(text: str) -> QWidget:
    """创建占位内容。"""
    w = QWidget()
    layout = QVBoxLayout(w)
    layout.addWidget(QLabel(text))
    return w


SPLITTER_STYLE = """
    QSplitter::handle {
        background: #cccccc;
        width: 2px;
        height: 2px;
        border: none;
        margin: 0;
    }
    QSplitter::handle:hover {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #4facfe, stop:0.5 #00f2fe, stop:1 #4facfe);
    }
"""


def _style_splitter(splitter):
    splitter.setStyleSheet(SPLITTER_STYLE)
    splitter.setChildrenCollapsible(False)


class _WorkspaceHostWidget(QWidget):
    """内部宿主：承载 layout 根 widget 与 overlay，resize 时自动更新 overlay 几何与层级。"""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._overlay: SplitPreviewOverlay | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

    def set_overlay(self, overlay: SplitPreviewOverlay) -> None:
        self._overlay = overlay
        self._update_overlay_geometry()

    def _update_overlay_geometry(self) -> None:
        if self._overlay is not None:
            self._overlay.setGeometry(self.rect())
            self._overlay.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_overlay_geometry()


class ContentConfig:
    """仿 CDockWidget：先创建、再 set_widget/set_window_title/set_icon、最后由 manager.place_content 加入布局。"""

    __slots__ = ("content_id", "_widget", "_title", "_icon")

    def __init__(self, content_id: str) -> None:
        self.content_id = content_id
        self._widget: QWidget | None = None
        self._title: str | None = None
        self._icon: QIcon | None = None

    def set_widget(self, w: QWidget) -> "ContentConfig":
        self._widget = w
        return self

    def set_window_title(self, title: str) -> "ContentConfig":
        self._title = title
        return self

    def set_icon(self, icon: QIcon | None) -> "ContentConfig":
        self._icon = icon
        return self


class WorkspaceManager:
    """工作区管理：根节点、LayoutTree、overlay、拖拽、窗格/内容工厂与拆分 API。对外提供 widget()，ADS 式用法：layout.addWidget(manager.widget())。"""

    def __init__(self, parent: QWidget | None = None) -> None:
        self._host = _WorkspaceHostWidget(parent)
        self._container = self._host  # 根替换时操作 host 的 layout
        self._root = SplitNode(None)

        self._layout_tree = LayoutTree(#主要用这棵树来管理
            self._root,
            style_splitter=_style_splitter,
            on_root_replaced=self._on_root_replaced,
        )

        self._host.layout().addWidget(self._layout_tree.root().root_widget())
        self._overlay = SplitPreviewOverlay(self._host)
        self._host.set_overlay(self._overlay)

        self._pane_counter = 0
        self._content_counter = 0

        self._drop_handler = create_drop_handler(
            layout_tree=self._layout_tree,
            new_pane_factory=self._new_pane,
            find_pane_by_id=self._layout_tree.find_pane_by_id,
            preview_callback=self._on_preview,
            on_new_pane=self._register_pane,
        )

    def _on_root_replaced(self, old_root: SplitNode, new_root: SplitNode) -> None:
        """根被提升替换时，在容器的 layout 中把旧根 widget 换成新根 widget。"""
        self._root = new_root
        lay = self._container.layout()
        if lay is None:
            return
        old_w = old_root.root_widget()
        new_w = new_root.root_widget()
        for i in range(lay.count()):
            item = lay.itemAt(i)
            if item and item.widget() is old_w:
                lay.removeWidget(old_w)
                lay.insertWidget(i, new_w)
                new_w.show()
                break
        self._overlay.raise_()

    def widget(self) -> QWidget:
        """返回宿主 widget（含根视图与 overlay），调用方仅需 layout.addWidget(manager.widget())。"""
        return self._host

    def layout_tree(self) -> LayoutTree:
        return self._layout_tree

    def find_pane_by_content_id(self, content_id: str) -> PaneWidget | None:
        """根据 content_id（内容唯一 id）查找包含该内容的窗格。"""
        for pane in self._layout_tree.panes():
            if content_id in pane.content_ids():
                return pane
        return None

    def _new_pane(self) -> PaneWidget:
        self._pane_counter += 1
        return PaneWidget(pane_id=f"pane_{self._pane_counter}")

    def new_content_id(self) -> str:
        self._content_counter += 1
        return f"content_{self._content_counter}"

    def _register_pane(self, pane: PaneWidget) -> None:
        """内部注册：连接信号并设置 drop handler，供 create_drop_handler 的 on_new_pane 使用。"""
        pane.pane_empty.connect(self._on_pane_empty)
        pane.set_drop_handler(self._drop_handler)

    def _on_pane_empty(self, pane: PaneWidget) -> None:
        pane.pane_empty.disconnect(self._on_pane_empty)
        self._layout_tree.remove_pane(pane)

    def _get_or_create_center_pane(self) -> PaneWidget:
        """无根下窗格时创建并挂到根，否则返回当前默认目标窗格。"""
        target = self._layout_tree.get_default_target_pane()
        if target is not None:
            return target
        pane = self._new_pane()
        self._layout_tree.add_pane_to_root(pane)
        self._register_pane(pane)
        return pane

    def get_root_pane(self) -> PaneWidget:
        """返回根窗格，作为布局起点；无则懒创建并挂到根。"""
        return self._get_or_create_center_pane()

    def _placement_to_split_args(self, area: int) -> tuple[Qt.Orientation, bool]:
        """Placement -> (direction, insert_before)。"""
        if area == Placement.Left:
            return Qt.Horizontal, True
        if area == Placement.Right:
            return Qt.Horizontal, False
        if area == Placement.Top:
            return Qt.Vertical, True
        if area == Placement.Bottom:
            return Qt.Vertical, False
        return Qt.Horizontal, False

    def split(
        self,
        pane: PaneWidget,
        placement: int,
        *,
        ratio: float = 0.5,
    ) -> PaneWidget:
        """从指定 pane 切出新窗格并返回；ratio 为新窗格占该次两块的比重，仅当父节点恰有两子时生效。"""
        direction, insert_before = self._placement_to_split_args(placement)
        new_pane = self._new_pane()
        tree = self._layout_tree
        if tree.find_parent_of_pane(pane) is not None:
            tree.split(pane, direction, insert_before, new_pane)
        else:
            tree.add_pane_to_root(new_pane)
        self._register_pane(new_pane)
        parent = tree.find_parent_of_pane(new_pane)
        if parent is not None and len(parent.children) == 2:
            M = 1000
            new_idx = 0 if insert_before else 1
            other_idx = 1 - new_idx
            sizes = [0, 0]
            sizes[new_idx] = int(ratio * M)
            sizes[other_idx] = int((1 - ratio) * M)
            parent.splitter.setSizes(sizes)
        return new_pane

    def fill_pane(self, pane: PaneWidget, content_config: ContentConfig) -> None:
        """将已配置的 ContentConfig 填入指定 pane（内部转成 add_content）。
        若该 pane 中已存在 content_config.content_id，则使用新 content_id 添加为新 tab，保证每次调用都会多一个 tab。
        同一 pane 内每个 tab 由唯一 content_id 标识；要对同一 pane 添加多个 tab 需传入不同 content_id 或复用同一 config（此时会自动分配新 id）。
        """
        content_id = content_config.content_id
        if content_id in pane.content_ids():
            content_id = self.new_content_id()
        title = content_config._title if content_config._title is not None else content_config.content_id
        widget = content_config._widget if content_config._widget is not None else _make_placeholder_content(content_config.content_id)
        icon = content_config._icon
        pane.add_content(content_id, title, widget, icon=icon)

    def _on_preview(self, zone, target_pane) -> None:
        self._overlay.show_preview(zone, target_pane)


    def create_content_config(self, content_id: str | None = None) -> ContentConfig:
        """创建内容配置，content_id 为 None 时由内部自动分配。"""
        if content_id is None:
            content_id = self.new_content_id()
        return ContentConfig(content_id)

