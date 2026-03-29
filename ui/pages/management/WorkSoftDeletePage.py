"""未删除作品列表：首列勾选，批量软删除。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Union

from PySide6.QtCore import QModelIndex, Qt, Slot
from PySide6.QtWidgets import QAbstractItemView, QHBoxLayout, QVBoxLayout

from config import DATABASE
from controller.global_signal_bus import global_signals
from controller.message_service import MessageBoxService
from core.database.update import mark_delete
from darkeye_ui import LazyWidget
from darkeye_ui.components.button import Button
from darkeye_ui.components.token_table_view import TokenTableView
from ui.base.SqliteQueryTableModel import SqliteQueryTableModel
from ui.basic import ModelSearch


class WorkListWithCheckboxesModel(SqliteQueryTableModel):
    """在查询结果前插入一列复选框；勾选状态按 work_id 保存（SQL 首列为 work_id）。"""

    def __init__(self, sql: str, database: Union[str, Path], parent=None):
        super().__init__(sql, database, parent)
        self._checked_work_ids: set[int] = set()

    def checked_work_ids(self) -> set[int]:
        return set(self._checked_work_ids)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        n = len(self._headers)
        return n + 1 if n else 0

    def data(self, index: QModelIndex, role: int):
        row, col = index.row(), index.column()
        if col == 0:
            if role == Qt.ItemDataRole.CheckStateRole:
                if 0 <= row < len(self._data):
                    wid = self._data[row][0]
                    if wid is not None and int(wid) in self._checked_work_ids:
                        return Qt.CheckState.Checked
                    return Qt.CheckState.Unchecked
            return None
        inner_col = col - 1
        if role in (
            Qt.ItemDataRole.DisplayRole,
            Qt.ItemDataRole.EditRole,
        ):
            if 0 <= row < len(self._data) and 0 <= inner_col < len(self._headers):
                val = self._data[row][inner_col]
                return "" if val is None else str(val)
        return None

    def setData(self, index: QModelIndex, value, role: int = Qt.ItemDataRole.EditRole):
        if role != Qt.ItemDataRole.CheckStateRole or index.column() != 0:
            return False
        row = index.row()
        if not (0 <= row < len(self._data)):
            return False
        wid = self._data[row][0]
        if wid is None:
            return False
        work_id = int(wid)
        # PySide6：value 多为 CheckState 枚举，不可用 int(CheckState)；也可能为底层整型 0/2。
        checked = value == Qt.CheckState.Checked or (
            isinstance(value, int) and value == Qt.CheckState.Checked.value
        )
        if checked:
            self._checked_work_ids.add(work_id)
        else:
            self._checked_work_ids.discard(work_id)
        self.dataChanged.emit(
            index,
            index,
            [Qt.ItemDataRole.CheckStateRole],
        )
        return True

    def flags(self, index: QModelIndex):
        base = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if index.column() == 0:
            return base | Qt.ItemFlag.ItemIsUserCheckable
        return base

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section == 0:
                    return "选"
                inner = section - 1
                if 0 <= inner < len(self._headers):
                    return self._headers[inner]
            return str(section + 1)
        return None

    def refresh(self) -> bool:
        ok = super().refresh()
        if ok:
            self._checked_work_ids.clear()
        return ok


class WorkSoftDeletePage(LazyWidget):
    """批量将作品标记为软删除（进入回收站）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.msg = MessageBoxService(self)

    def _lazy_load(self):
        logging.info("----------作品软删除页面----------")
        self.init_ui()
        self.signal_connect()
        self.config()

    def config(self):
        self.model = WorkListWithCheckboxesModel(
            "SELECT * FROM work WHERE IFNULL(is_deleted, 0) = 0",
            DATABASE,
            self,
        )
        if not self.model.refresh():
            self.msg.show_critical("错误", "无法加载数据，请查看日志。")
            return

        self.view.setModel(self.model)
        self.view.setColumnHidden(1, True)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.searchWidget.set_model_view(self.model, self.view)

    def init_ui(self):
        self.view = TokenTableView()
        self.btn_refresh = Button("刷新数据")
        self.btn_soft_delete = Button("软删除选中")

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.btn_refresh)
        button_layout.addWidget(self.btn_soft_delete)

        self.searchWidget = ModelSearch()

        layout = QVBoxLayout(self)
        layout.addWidget(self.view)
        layout.addWidget(self.searchWidget)
        layout.addLayout(button_layout)

    def signal_connect(self):
        self.btn_refresh.clicked.connect(self.refresh_data)
        self.btn_soft_delete.clicked.connect(self.soft_delete_checked)

    @Slot()
    def refresh_data(self):
        if not self.model.refresh():
            self.msg.show_critical("查询错误", "刷新数据失败，请查看日志。")
            return
        logging.info("数据已刷新")

    @Slot()
    def soft_delete_checked(self):
        ids = self.model.checked_work_ids()
        if not ids:
            self.msg.show_warning("提示", "请先勾选要软删除的作品")
            return

        n = len(ids)
        if not self.msg.ask_yes_no(
            "确认软删除",
            f"确定将选中的 {n} 部作品移入回收站吗？可在回收站恢复。",
        ):
            return

        for work_id in ids:
            if not mark_delete(work_id):
                self.msg.show_critical("错误", f"软删除失败，work_id={work_id}")
                return

        global_signals.workDataChanged.emit()
        self.refresh_data()
        self.msg.show_info("成功", f"已将 {n} 部作品移入回收站")
