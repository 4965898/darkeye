"""
阶段一：PaneWidget = TabBar + StackedWidget，支持 Tab 顺序拖拽与关闭。
测试文件在tests/test_pane_widget.py
"""
from typing import Callable

from PySide6.QtWidgets import (
    QTabBar,
    QStackedWidget,
    QWidget,
    QVBoxLayout,
)
from PySide6.QtCore import Signal, Qt, QPoint, QMimeData, QEvent
from PySide6.QtGui import (
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
    QDragLeaveEvent,
    QDrag,
    QIcon,
)


MIME_TYPE_TAB = "application/x-workspace-demo-tab"

_DRAG_THRESHOLD = 8




class ClosableTabBar(QTabBar):
    """支持关闭按钮的 TabBar；关闭时发出 tab_close_requested(index)，是否为空由 PaneWidget 判断。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMovable(True)
        self.setTabsClosable(True)
        self.setExpanding(False)
        self.setObjectName("WorkspaceDemoTabBar")

class DraggableTabBar(ClosableTabBar):
    """支持跨窗格拖拽的 TabBar。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_start_pos: QPoint | None = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start_pos is None:
            super().mouseMoveEvent(event)
            return
        if (event.buttons() & Qt.LeftButton) == 0:
            super().mouseMoveEvent(event)
            return
        diff = event.position().toPoint() - self._drag_start_pos
        if diff.manhattanLength() < _DRAG_THRESHOLD:
            super().mouseMoveEvent(event)
            return

        idx = self.tabAt(self._drag_start_pos)
        if idx < 0:
            super().mouseMoveEvent(event)
            return

        # 若仍停留在 Tab 栏内，交由 Qt 内置 setMovable(True) 处理同一窗格内的 Tab 重排
        pos = event.position().toPoint()
        if self.rect().contains(pos):
            super().mouseMoveEvent(event)
            return

        # 鼠标已移出 Tab 栏：先让 Qt 处理事件以结束其内部拖拽，避免 Tab 卡住
        super().mouseMoveEvent(event)
        # 再启动跨窗格拖拽
        content_id = self.tabData(idx)
        title = self.tabText(idx)
        pane = self.parent()
        if not isinstance(pane, PaneWidget):
            return

        mime = QMimeData()
        mime.setData(
            MIME_TYPE_TAB,
            f"{content_id}\n{pane.pane_id}\n{title}".encode("utf-8"),
        )
        drag = QDrag(self)
        drag.setMimeData(mime)
        drag.exec(Qt.MoveAction)
        self._drag_start_pos = None


class PaneWidget(QWidget):
    """窗格 = Tab 栏 + 内容区（StackedWidget），每个 Tab 对应一个内容页。"""

    pane_empty = Signal(object)  # 参数为 self（被关闭的 PaneWidget）

    def __init__(self, pane_id: str = "", parent=None):
        super().__init__(parent)
        self._pane_id = pane_id or id(self).__hex__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.force_drop_interception=False#是否强制拦截drop事件

        self._tab_bar = DraggableTabBar(self)
        #self._tab_bar.tab_close_requested.connect(self._on_tab_close_requested)
        self._tab_bar.tabCloseRequested.connect(self._on_tab_close_requested)
        self._tab_bar.setAcceptDrops(True)
        layout.addWidget(self._tab_bar)

        self._stack = QStackedWidget(self)
        self._stack.setAcceptDrops(True)
        layout.addWidget(self._stack, 1)

        self._tab_bar.currentChanged.connect(self._stack.setCurrentIndex)
        self._tab_bar.tabMoved.connect(self._on_tab_moved)

        self.setAcceptDrops(True)
        self._drop_handler = None  # 由 WorkspaceDemoWidget 设置

        # 子控件会拦截 drop，安装事件过滤器转发拖放事件到 Pane
        self._tab_bar.installEventFilter(self)
        self._stack.installEventFilter(self)

    @property
    def pane_id(self) -> str:
        return self._pane_id

    def _index_for_content_id(self, content_id: str) -> int | None:
        """根据 content_id 在 TabBar 中的索引，不存在返回 None。"""
        for i in range(self._tab_bar.count()):
            if self._tab_bar.tabData(i) == content_id:
                return i
        return None

    def _install_drop_forwarding(self, w: QWidget) -> None:
        """递归为 widget 及其子控件启用 drop 转发。
        这个里面东西多了以后会有性能问题
        这个东西不是必须的，除非子控件有子控件设置 acceptDrops(True)
        比如QTextEdit
        QGraphicsView
        QTreeView
        """
        if self.force_drop_interception:
            if w is self._tab_bar or w is self._stack:
                return
            w.setAcceptDrops(True)
            w.installEventFilter(self)
            for child in w.findChildren(QWidget):
                if child.parent() is w:
                    self._install_drop_forwarding(child)
                
        

    def _uninstall_drop_forwarding(self, w: QWidget) -> None:
        """递归移除 drop 转发。"""
        pass
        if self.force_drop_interception:
            if w is self._tab_bar or w is self._stack:
                return
            w.removeEventFilter(self)
            for child in w.findChildren(QWidget):
                if child.parent() is w:
                    self._uninstall_drop_forwarding(child)

    def add_content(
        self, content_id: str, title: str, widget: QWidget, icon: QIcon | None = None
    ) -> None:
        """添加一个内容页，若已存在则更新标题与图标。"""
        self._install_drop_forwarding(widget)
        idx = self._index_for_content_id(content_id)
        if idx is not None:
            old_w = self._stack.widget(idx)
            if old_w:
                self._uninstall_drop_forwarding(old_w)
                old_w.removeEventFilter(self)
            self._tab_bar.setTabText(idx, title)
            if icon is not None:
                self._tab_bar.setTabIcon(idx, icon)
            else:
                self._tab_bar.setTabIcon(idx, QIcon())
            self._stack.removeWidget(old_w)
            self._stack.insertWidget(idx, widget)
            self._tab_bar.setCurrentIndex(idx)
            self._stack.setCurrentIndex(idx)
            return
        idx = self._stack.addWidget(widget)
        if icon is not None:
            self._tab_bar.addTab(icon, title)
        else:
            self._tab_bar.addTab(title)
        self._tab_bar.setTabData(idx, content_id)
        self._tab_bar.setCurrentIndex(idx)
        self._stack.setCurrentIndex(idx)
        self._tab_bar.updateGeometry()
        self.updateGeometry()#更新布局  


    def _on_tab_close_requested(self, index: int) -> None:
        """Tab 关闭请求：按 content_id 移除内容，空则发出 pane_empty（empty 判断在此统一处理）。"""
        content_id = self._tab_bar.tabData(index)
        if content_id is not None:
            self.remove_content(content_id)


    def remove_content(self, content_id: str) -> bool:
        """移除内容页，返回是否成功。"""
        idx = self._index_for_content_id(content_id)
        if idx is None:
            return False
        self._tab_bar.removeTab(idx)
        w = self._stack.widget(idx)
        if w:
            self._uninstall_drop_forwarding(w)
        self._stack.removeWidget(w)
        if self._tab_bar.count() == 0:
            self.pane_empty.emit(self)
        return True

    def current_content_id(self) -> str | None:
        """当前选中 Tab 对应的 content_id。"""
        idx = self._tab_bar.currentIndex()
        if idx < 0:
            return None
        cid = self._tab_bar.tabData(idx)
        return cid if isinstance(cid, str) else None

    def content_ids(self) -> list[str]:
        """所有内容 ID 列表。"""
        return [
            cid
            for i in range(self._tab_bar.count())
            if (cid := self._tab_bar.tabData(i)) is not None
        ]

    def content_count(self) -> int:
        return self._tab_bar.count()

    def _on_tab_moved(self, from_index: int, to_index: int) -> None:
        """Tab 栏内拖拽重排时，同步 StackedWidget 顺序。"""
        w = self._stack.widget(from_index)
        if w is None:
            return
        self._stack.removeWidget(w)
        self._stack.insertWidget(to_index, w)


    def get_content_widget(self, content_id: str) -> QWidget | None:
        """根据 content_id 获取内容 widget。"""
        idx = self._index_for_content_id(content_id)
        if idx is None:
            return None
        return self._stack.widget(idx)

    def get_icon_for_content(self, content_id: str) -> QIcon | None:
        """根据 content_id 获取关联的 Tab 图标（从 TabBar 按索引读取，无需单独缓存）。"""
        idx = self._index_for_content_id(content_id)
        if idx is None:
            return None
        icon = self._tab_bar.tabIcon(idx)
        return icon if not icon.isNull() else None

    def set_drop_handler(self, handler: Callable[..., bool | None] | None) -> None:
        """设置拖放处理器，用于跨窗格 DND。handler(event_type, event, pane, pos_in_pane=None)。"""
        self._drop_handler = handler

    def eventFilter(self, obj, event):
        """将子控件（TabBar/Stack）收到的拖放事件转发给 Pane 的 drop handler。处理时返回 True 表示已消费事件。
        重定向拖拽事件归属权。
        """
        t = event.type()
        if t == QEvent.DragLeave:
            if self._drop_handler:
                self._drop_handler("leave", event, self)
            return super().eventFilter(obj, event)#如果是离开事件继续交给qt处理
        if t in (QEvent.DragEnter, QEvent.DragMove, QEvent.Drop) and self._drop_handler:#只处理自己的拖拽
            mime = event.mimeData() if hasattr(event, "mimeData") else None
            if mime and mime.hasFormat(MIME_TYPE_TAB):
                pos_in_pane = self._map_pos_for_child(obj, event)
                if t == QEvent.DragEnter:
                    if self._drop_handler("enter", event, self, pos_in_pane):
                        event.acceptProposedAction()
                    return True#事件已经被消费，不再传给父控件
                if t == QEvent.DragMove:
                    if self._drop_handler("move", event, self, pos_in_pane):
                        event.acceptProposedAction()
                    return True
                if t == QEvent.Drop:#在控件内释放鼠标
                    handled = self._drop_handler("drop", event, self, pos_in_pane)
                    if handled:
                        event.acceptProposedAction()
                    return True
        return super().eventFilter(obj, event)

    def _map_pos_for_child(self, child: QWidget, event) -> QPoint:
        """将子控件坐标系下的位置映射到 Pane 坐标系。"""
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        return child.mapTo(self, pos)

    def _pos_in_pane_from_event(self, event) -> QPoint:
        """从拖放事件取得 Pane 坐标系下的位置（事件直接落在 Pane 时使用）。"""
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        return pos

    def dragEnterEvent(self, event: QDragEnterEvent):
        if self._drop_handler and event.mimeData().hasFormat(MIME_TYPE_TAB):
            pos = self._pos_in_pane_from_event(event)
            if self._drop_handler("enter", event, self, pos):
                event.acceptProposedAction()

    def dragMoveEvent(self, event: QDragMoveEvent):
        if self._drop_handler and event.mimeData().hasFormat(MIME_TYPE_TAB):
            pos = self._pos_in_pane_from_event(event)
            if self._drop_handler("move", event, self, pos):
                event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        if self._drop_handler and event.mimeData().hasFormat(MIME_TYPE_TAB):
            pos = self._pos_in_pane_from_event(event)
            if self._drop_handler("drop", event, self, pos):
                event.acceptProposedAction()

    def dragLeaveEvent(self, event: QDragLeaveEvent):
        if self._drop_handler:
            self._drop_handler("leave", event, self)
