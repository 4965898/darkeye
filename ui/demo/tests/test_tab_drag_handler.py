"""单元测试：tab_drag_handler 的 hit_test 与 drop_handler 正确性。"""
import sys
import os
from unittest.mock import Mock, MagicMock

import pytest

import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parents[3]  
sys.path.insert(0, str(root_dir))

from PySide6.QtCore import QPoint, QRect, Qt

from ui.demo.tab_drag_handler import (
    DropZone,
    hit_test,
    create_drop_handler,
)
from ui.demo.pane_widget import MIME_TYPE_TAB


class TestHitTest:
    """hit_test(pane_rect, pos) 区域与边界。"""

    def test_invalid_rect_zero_size(self):
        """width 或 height <= 0 时返回 CENTER。"""
        rect_w0 = QRect(0, 0, 0, 100)
        rect_h0 = QRect(0, 0, 100, 0)
        rect_both = QRect(0, 0, 0, 0)
        pos = QPoint(50, 50)
        assert hit_test(rect_w0, pos) == DropZone.CENTER
        assert hit_test(rect_h0, pos) == DropZone.CENTER
        assert hit_test(rect_both, pos) == DropZone.CENTER

    def test_top_zone(self):
        """上 20% 返回 TOP。"""
        r = QRect(0, 0, 100, 100)  # top_edge=20
        assert hit_test(r, QPoint(10, 0)) == DropZone.TOP
        assert hit_test(r, QPoint(50, 19)) == DropZone.TOP

    def test_bottom_zone(self):
        """下 20% 返回 BOTTOM。"""
        r = QRect(0, 0, 100, 100)  # bottom_edge=80
        assert hit_test(r, QPoint(50, 80)) == DropZone.BOTTOM
        assert hit_test(r, QPoint(50, 99)) == DropZone.BOTTOM

    def test_left_zone(self):
        """左 20% 返回 LEFT。"""
        r = QRect(0, 0, 100, 100)  # left_edge=20
        assert hit_test(r, QPoint(0, 50)) == DropZone.LEFT
        assert hit_test(r, QPoint(19, 50)) == DropZone.LEFT

    def test_right_zone(self):
        """右 20% 返回 RIGHT。"""
        r = QRect(0, 0, 100, 100)  # right_edge=80
        assert hit_test(r, QPoint(80, 50)) == DropZone.RIGHT
        assert hit_test(r, QPoint(99, 50)) == DropZone.RIGHT

    def test_center_zone(self):
        """中间 60%×60% 返回 CENTER。"""
        r = QRect(0, 0, 100, 100)
        assert hit_test(r, QPoint(20, 20)) == DropZone.CENTER
        assert hit_test(r, QPoint(50, 50)) == DropZone.CENTER
        assert hit_test(r, QPoint(79, 79)) == DropZone.CENTER

    def test_boundary_edges(self):
        """恰好在 0.2/0.8 边界：x=20 或 y=20 为 CENTER，x=80 或 y=80 为 RIGHT/BOTTOM。"""
        r = QRect(0, 0, 100, 100)
        assert hit_test(r, QPoint(20, 50)) == DropZone.CENTER
        assert hit_test(r, QPoint(50, 20)) == DropZone.CENTER
        assert hit_test(r, QPoint(80, 50)) == DropZone.RIGHT
        assert hit_test(r, QPoint(50, 80)) == DropZone.BOTTOM


class TestDropHandler:
    """create_drop_handler 返回的 drop_handler 各分支。"""

    def _make_mock_event(self, has_mime=True, mime_payload=None, pos=None):
        if pos is None:
            pos = QPoint(50, 50)
        mime = Mock()
        mime.hasFormat = Mock(return_value=has_mime)
        if mime_payload is not None:
            mime.data = Mock(return_value=mime_payload)
        event = Mock()
        event.mimeData = Mock(return_value=mime)
        event.position = Mock(return_value=Mock(toPoint=Mock(return_value=pos)))
        event.acceptProposedAction = Mock()
        return event

    def _make_mock_pane(self, rect=None, get_content_widget_result=MagicMock(), get_icon_result=None):
        if rect is None:
            rect = QRect(0, 0, 100, 100)
        pane = Mock()
        pane.rect = Mock(return_value=rect)
        pane.get_content_widget = Mock(return_value=get_content_widget_result)
        pane.get_icon_for_content = Mock(return_value=get_icon_result)
        return pane

    def test_leave_calls_preview_callback(self):
        """leave 时若提供 preview_callback，则调用 preview_callback(None, None)。"""
        preview = Mock()
        handler = create_drop_handler(Mock(), Mock(), Mock(), preview_callback=preview)
        event = self._make_mock_event()
        pane = self._make_mock_pane()
        handler("leave", event, pane)
        preview.assert_called_once_with(None, None)

    def test_leave_no_preview_no_error(self):
        """leave 且无 preview_callback 时不报错。"""
        handler = create_drop_handler(Mock(), Mock(), Mock())
        handler("leave", self._make_mock_event(), self._make_mock_pane())

    def test_enter_without_mime_returns_false(self):
        """enter 且无 MIME_TYPE_TAB 时返回 False。"""
        handler = create_drop_handler(Mock(), Mock(), Mock())
        event = self._make_mock_event(has_mime=False)
        pane = self._make_mock_pane()
        result = handler("enter", event, pane)
        assert result is False
        event.acceptProposedAction.assert_not_called()

    def test_enter_with_mime_accepts_and_returns_true(self):
        """enter 且有 MIME_TYPE_TAB 时 accept 并返回 True。"""
        handler = create_drop_handler(Mock(), Mock(), Mock())
        event = self._make_mock_event(has_mime=True)
        pane = self._make_mock_pane()
        result = handler("enter", event, pane)
        assert result is True
        event.acceptProposedAction.assert_called_once()

    def test_move_with_mime_calls_preview_and_accepts(self):
        """move 且有 MIME 时调用 preview_callback(zone, pane) 并 accept，返回 True。"""
        preview = Mock()
        handler = create_drop_handler(Mock(), Mock(), Mock(), preview_callback=preview)
        pos = QPoint(10, 10)  # TOP zone in 100x100
        event = self._make_mock_event(has_mime=True, pos=pos)
        pane = self._make_mock_pane()
        result = handler("move", event, pane)
        assert result is True
        preview.assert_called_once_with(DropZone.TOP, pane)
        event.acceptProposedAction.assert_called_once()

    def test_drop_mime_insufficient_returns_false(self):
        """drop 时 MIME 不足 3 行返回 False。"""
        handler = create_drop_handler(Mock(), Mock(), Mock())
        payload = "id1\npane1".encode("utf-8")  # 只有 2 行
        event = self._make_mock_event(has_mime=True, mime_payload=payload)
        pane = self._make_mock_pane()
        result = handler("drop", event, pane)
        assert result is False

    def test_drop_source_pane_not_found_returns_false(self):
        """drop 时 find_pane_by_id 返回 None 则返回 False。"""
        find_pane = Mock(return_value=None)
        handler = create_drop_handler(Mock(), Mock(), find_pane)
        payload = "cid\nsource-pane\nTitle".encode("utf-8")
        event = self._make_mock_event(has_mime=True, mime_payload=payload)
        pane = self._make_mock_pane()
        result = handler("drop", event, pane)
        assert result is False

    def test_drop_source_equals_target_center_returns_false(self):
        """drop 到 CENTER 且 source_pane == pane（同窗格合并到自己）返回 False。"""
        pane = self._make_mock_pane()
        find_pane = Mock(return_value=pane)
        handler = create_drop_handler(Mock(), Mock(), find_pane)
        payload = "cid\nsource-pane\nTitle".encode("utf-8")
        pos = QPoint(50, 50)  # CENTER
        event = self._make_mock_event(has_mime=True, mime_payload=payload, pos=pos)
        result = handler("drop", event, pane)
        assert result is False

    def test_drop_same_pane_edge_split_succeeds(self):
        """同窗格内拖到边缘（TOP）应拆分，不拒绝。"""
        widget = Mock()
        pane = self._make_mock_pane(get_content_widget_result=widget)
        new_pane = self._make_mock_pane()
        find_pane = Mock(return_value=pane)
        new_pane_factory = Mock(return_value=new_pane)
        layout_tree = Mock()
        handler = create_drop_handler(layout_tree, new_pane_factory, find_pane)
        payload = "cid\npane-1\nTitle".encode("utf-8")
        pos = QPoint(50, 10)  # TOP zone
        event = self._make_mock_event(has_mime=True, mime_payload=payload, pos=pos)
        result = handler("drop", event, pane)
        assert result is True
        layout_tree.split.assert_called_once_with(
            pane, Qt.Vertical, True, new_pane
        )

    def test_drop_widget_not_found_returns_false(self):
        """drop 时 get_content_widget 返回 None 则返回 False。"""
        source_pane = self._make_mock_pane(get_content_widget_result=None)
        target_pane = self._make_mock_pane()
        find_pane = Mock(return_value=source_pane)
        handler = create_drop_handler(Mock(), Mock(), find_pane)
        payload = "cid\nsource-pane\nTitle".encode("utf-8")
        event = self._make_mock_event(has_mime=True, mime_payload=payload)
        result = handler("drop", event, target_pane)
        assert result is False

    def test_drop_center_merge_calls_remove_and_add_no_split(self):
        """drop 到 CENTER 时：source remove、pane add，不调用 new_pane_factory/split。"""
        widget = Mock()
        source_pane = self._make_mock_pane(get_content_widget_result=widget)
        target_pane = self._make_mock_pane()
        find_pane = Mock(return_value=source_pane)
        layout_tree = Mock()
        new_pane_factory = Mock()
        handler = create_drop_handler(layout_tree, new_pane_factory, find_pane)
        payload = "cid\nsource-pane\nTitle".encode("utf-8")
        pos = QPoint(50, 50)  # center
        event = self._make_mock_event(has_mime=True, mime_payload=payload, pos=pos)
        result = handler("drop", event, target_pane)
        assert result is True
        source_pane.remove_content.assert_called_once_with("cid")
        target_pane.add_content.assert_called_once_with("cid", "Title", widget, icon=None)
        new_pane_factory.assert_not_called()
        layout_tree.split.assert_not_called()

    def test_drop_top_splits_vertical_insert_before(self):
        """drop 到 TOP：new_pane、remove、add 到 new_pane、split(Vertical, insert_before=True)。"""
        widget = Mock()
        source_pane = self._make_mock_pane(get_content_widget_result=widget)
        target_pane = self._make_mock_pane()
        new_pane = self._make_mock_pane()
        find_pane = Mock(return_value=source_pane)
        new_pane_factory = Mock(return_value=new_pane)
        layout_tree = Mock()
        handler = create_drop_handler(layout_tree, new_pane_factory, find_pane)
        payload = "cid\nsource-pane\nTitle".encode("utf-8")
        pos = QPoint(50, 10)  # TOP
        event = self._make_mock_event(has_mime=True, mime_payload=payload, pos=pos)
        result = handler("drop", event, target_pane)
        assert result is True
        new_pane_factory.assert_called_once()
        source_pane.remove_content.assert_called_once_with("cid")
        new_pane.add_content.assert_called_once_with("cid", "Title", widget, icon=None)
        layout_tree.split.assert_called_once_with(
            target_pane, Qt.Vertical, True, new_pane
        )

    def test_drop_bottom_splits_vertical_insert_after(self):
        """drop 到 BOTTOM：split(Vertical, insert_before=False)。"""
        widget = Mock()
        source_pane = self._make_mock_pane(get_content_widget_result=widget)
        target_pane = self._make_mock_pane()
        new_pane = self._make_mock_pane()
        find_pane = Mock(return_value=source_pane)
        new_pane_factory = Mock(return_value=new_pane)
        layout_tree = Mock()
        handler = create_drop_handler(layout_tree, new_pane_factory, find_pane)
        payload = "cid\nsource-pane\nTitle".encode("utf-8")
        pos = QPoint(50, 85)  # BOTTOM
        event = self._make_mock_event(has_mime=True, mime_payload=payload, pos=pos)
        result = handler("drop", event, target_pane)
        assert result is True
        layout_tree.split.assert_called_once_with(
            target_pane, Qt.Vertical, False, new_pane
        )

    def test_drop_left_splits_horizontal_insert_before(self):
        """drop 到 LEFT：split(Horizontal, insert_before=True)。"""
        widget = Mock()
        source_pane = self._make_mock_pane(get_content_widget_result=widget)
        target_pane = self._make_mock_pane()
        new_pane = self._make_mock_pane()
        find_pane = Mock(return_value=source_pane)
        new_pane_factory = Mock(return_value=new_pane)
        layout_tree = Mock()
        handler = create_drop_handler(layout_tree, new_pane_factory, find_pane)
        payload = "cid\nsource-pane\nTitle".encode("utf-8")
        pos = QPoint(10, 50)  # LEFT
        event = self._make_mock_event(has_mime=True, mime_payload=payload, pos=pos)
        result = handler("drop", event, target_pane)
        assert result is True
        layout_tree.split.assert_called_once_with(
            target_pane, Qt.Horizontal, True, new_pane
        )

    def test_drop_right_splits_horizontal_insert_after(self):
        """drop 到 RIGHT：split(Horizontal, insert_before=False)。"""
        widget = Mock()
        source_pane = self._make_mock_pane(get_content_widget_result=widget)
        target_pane = self._make_mock_pane()
        new_pane = self._make_mock_pane()
        find_pane = Mock(return_value=source_pane)
        new_pane_factory = Mock(return_value=new_pane)
        layout_tree = Mock()
        handler = create_drop_handler(layout_tree, new_pane_factory, find_pane)
        payload = "cid\nsource-pane\nTitle".encode("utf-8")
        pos = QPoint(85, 50)  # RIGHT
        event = self._make_mock_event(has_mime=True, mime_payload=payload, pos=pos)
        result = handler("drop", event, target_pane)
        assert result is True
        layout_tree.split.assert_called_once_with(
            target_pane, Qt.Horizontal, False, new_pane
        )

    def test_drop_split_calls_on_new_pane(self):
        """drop 到非 CENTER 且提供 on_new_pane 时，调用 on_new_pane(new_pane)。"""
        widget = Mock()
        source_pane = self._make_mock_pane(get_content_widget_result=widget)
        target_pane = self._make_mock_pane()
        new_pane = self._make_mock_pane()
        find_pane = Mock(return_value=source_pane)
        new_pane_factory = Mock(return_value=new_pane)
        layout_tree = Mock()
        on_new_pane = Mock()
        handler = create_drop_handler(
            layout_tree, new_pane_factory, find_pane, on_new_pane=on_new_pane
        )
        payload = "cid\nsource-pane\nTitle".encode("utf-8")
        pos = QPoint(50, 10)  # TOP
        event = self._make_mock_event(has_mime=True, mime_payload=payload, pos=pos)
        handler("drop", event, target_pane)
        on_new_pane.assert_called_once_with(new_pane)

    def test_drop_uses_pos_in_pane_when_given(self):
        """drop 时若传入 pos_in_pane，则用其做 hit_test，不读 event.position。"""
        widget = Mock()
        source_pane = self._make_mock_pane(get_content_widget_result=widget)
        target_pane = self._make_mock_pane()
        new_pane = self._make_mock_pane()
        find_pane = Mock(return_value=source_pane)
        new_pane_factory = Mock(return_value=new_pane)
        layout_tree = Mock()
        handler = create_drop_handler(layout_tree, new_pane_factory, find_pane)
        payload = "cid\nsource-pane\nTitle".encode("utf-8")
        event = self._make_mock_event(has_mime=True, mime_payload=payload, pos=QPoint(0, 0))
        # pos_in_pane 在中心 -> 应合并到 target，不拆分
        result = handler("drop", event, target_pane, pos_in_pane=QPoint(50, 50))
        assert result is True
        layout_tree.split.assert_not_called()
        target_pane.add_content.assert_called_once_with("cid", "Title", widget, icon=None)
