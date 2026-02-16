"""阶段三：Tab 拖拽逻辑与几何计算（DND）。"""

from enum import Enum
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication

from ui.demo.pane_widget import PaneWidget, MIME_TYPE_TAB


class DropZone(Enum):
    """拖放目标区域。"""
    TOP = "top"       # 上 20% → 上方拆分
    BOTTOM = "bottom" # 下 20% → 下方拆分
    LEFT = "left"     # 左 20% → 左侧拆分
    RIGHT = "right"   # 右 20% → 右侧拆分
    CENTER = "center" # 中间 60%×60% → 合并到当前窗格


def hit_test(pane_rect, pos: QPoint) -> DropZone:
    """根据 Pane 内相对位置计算落入的区域。"""
    x = pos.x()
    y = pos.y()
    w = pane_rect.width()
    h = pane_rect.height()
    if w <= 0 or h <= 0:
        return DropZone.CENTER

    left_edge = w * 0.2
    right_edge = w * 0.8
    top_edge = h * 0.2
    bottom_edge = h * 0.8

    if y < top_edge:
        return DropZone.TOP
    if y >= bottom_edge:
        return DropZone.BOTTOM
    if x < left_edge:
        return DropZone.LEFT
    if x >= right_edge:
        return DropZone.RIGHT
    return DropZone.CENTER


def create_drop_handler(
    layout_tree,
    new_pane_factory,
    find_pane_by_id,
    preview_callback=None,
    on_new_pane=None,
):
    """
    创建 drop_handler 供 PaneWidget.set_drop_handler 使用。
    返回 (event_type, event, pane) -> bool 的 callable。
    """

    def drop_handler(event_type: str, event, pane: PaneWidget, pos_in_pane=None)->bool:
        if event_type == "leave":#清除预览区域
            if preview_callback:
                preview_callback(None, None)
            return

        if not event.mimeData().hasFormat(MIME_TYPE_TAB):
            return False

        def get_pos():
            if pos_in_pane is not None:
                return pos_in_pane
            return event.position().toPoint() if hasattr(event, "position") else event.pos()

        if event_type == "enter":
            event.acceptProposedAction()
            return True

        if event_type == "move":#计算预览的区域
            pos = get_pos()
            zone = hit_test(pane.rect(), pos)
            if preview_callback:
                preview_callback(zone, pane)
            event.acceptProposedAction()
            return True

        if event_type == "drop":#在控件内释放鼠标
            if preview_callback:
                preview_callback(None, None)
            data = bytes(event.mimeData().data(MIME_TYPE_TAB)).decode("utf-8")
            parts = data.strip().split("\n")
            if len(parts) < 3:
                return False
            content_id, source_pane_id, title = parts[0], parts[1], parts[2]
            source_pane:PaneWidget = find_pane_by_id(source_pane_id)
            if not source_pane:
                return False

            pos = get_pos()
            zone = hit_test(pane.rect(), pos)
            # 仅 CENTER 且同窗格时拒绝（合并到自己无意义）；边缘拆分允许同窗格
            if zone == DropZone.CENTER and source_pane == pane:
                return False

            widget = source_pane.get_content_widget(content_id)
            if not widget:
                return False

            icon = source_pane.get_icon_for_content(content_id)
            if zone == DropZone.CENTER:
                # 合并到当前窗格
                source_pane.remove_content(content_id)
                pane.add_content(content_id, title, widget, icon=icon)
            else:
                # 拆分：先加入布局再移动内容，避免单 tab 时 remove_content 触发 pane_empty 导致 split 时 pane 已不在树中
                new_pane = new_pane_factory()
                orientation = Qt.Horizontal if zone in (DropZone.LEFT, DropZone.RIGHT) else Qt.Vertical
                insert_before = zone in (DropZone.TOP, DropZone.LEFT)
                layout_tree.split(pane, orientation, insert_before, new_pane)
                if on_new_pane:
                    on_new_pane(new_pane)
                source_pane.remove_content(content_id)
                new_pane.add_content(content_id, title, widget, icon=icon)

            event.acceptProposedAction()
            return True

        return False

    return drop_handler
