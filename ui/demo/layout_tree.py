"""阶段二：布局树与 QSplitter 动态管理。"""
'''测试文件在tests/'''
from PySide6.QtWidgets import QSplitter, QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from typing import Union, Callable

from ui.demo.pane_widget import PaneWidget


SplitChild = Union["SplitNode", PaneWidget]

# 用于 QSplitter.setSizes 的近似 1:1 均分（大数让 Qt 按比例分配）
EQUAL_SPLIT_SIZES = [9999, 9999]


def _widget_of(node: SplitChild) -> QWidget:
    """从 SplitChild 取实际要加入布局的 widget（PaneWidget 自身或 SplitNode.splitter）。"""
    return node if isinstance(node, PaneWidget) else node.splitter


def _dump_node(node: SplitChild, indent: int = 0) -> list[str]:
    """递归收集树节点信息，返回多行字符串。"""
    lines = []
    prefix = "  " * indent
    if isinstance(node, SplitNode):
        orient = (
            "H"
            if node.orientation == Qt.Horizontal
            else ("V" if node.orientation == Qt.Vertical else "—")
        )
        lines.append(f"{prefix}Split({orient}) children={len(node.children)}")
        for child in node.children:
            lines.extend(_dump_node(child, indent + 1))
    else:
        if not isinstance(node, PaneWidget):
            raise TypeError(f"Expected PaneWidget, got {type(node).__name__}")
        tabs = []
        for i in range(node._tab_bar.count()):
            cid = node._tab_bar.tabData(i) or ""
            title = node._tab_bar.tabText(i)
            tabs.append(f"{cid}:{title}")
        lines.append(f"{prefix}Pane(id={node.pane_id}) tabs={tabs}")
    return lines


class SplitNode:
    """持有 QSplitter 或单窗格容器，子节点为 SplitNode 或 PaneWidget。orientation 为 None 时表示无方向（仅单 pane）。"""

    def __init__(
        self,
        orientation: Qt.Orientation | None = None,
        parent_splitter: QSplitter | None = None,
    ):
        self.orientation = orientation
        self.children: list[SplitChild] = []#两种东西一种SplitNode一种PaneWidget
        self._parent_splitter = parent_splitter
        self._parent_node: SplitNode | None = None

        if orientation is None:#无方向的时候没有splitter，只有container
            self._container = QWidget()
            self._container.setLayout(QVBoxLayout())
            self._container.layout().setContentsMargins(0, 0, 0, 0)
            self._splitter: QSplitter | None = None
        else:
            self._container = None
            self._splitter = QSplitter(orientation)

    @property
    def splitter(self) -> QSplitter | QWidget:
        """有方向时返回 QSplitter，无方向时返回 _container（用于 add_child 等）。"""
        if self._splitter is not None:
            return self._splitter
        assert self._container is not None
        return self._container

    def root_widget(self) -> QWidget:
        """主布局应添加的根 widget：有 _container 时返回 _container，否则返回 _splitter。"""
        if self._container is not None:
            return self._container
        assert self._splitter is not None
        return self._splitter

    def add_child(self, child: SplitChild, index: int = -1) -> None:
        """添加子节点。"""
        w = _widget_of(child)
        if self.orientation is None:
            # 无方向：仅支持单子，放入 _container 的 layout
            lay = self._container.layout()
            if index >= 0:
                lay.insertWidget(index, w)
                self.children.insert(index, child)
            else:
                lay.addWidget(w)
                self.children.append(child)
            w.show()
        else:#有方向
            self._splitter.insertWidget(
                index if index >= 0 else self._splitter.count(), w
            )
            w.show()
            if index >= 0:
                self.children.insert(index, child)
            else:
                self.children.append(child)
        self._set_parent(child)

    def _set_parent(self, child: SplitChild) -> None:
        if isinstance(child, SplitNode):
            child._parent_node = self
            child._parent_splitter = self.splitter
        # PaneWidget 无树父引用，通过 WorkspaceWidget 的 layout_tree 管理

    def remove_child(self, child: SplitChild) -> bool:
        """移除子节点，返回是否成功。"""
        try:
            idx = self.children.index(child)
        except ValueError:
            return False
        w = _widget_of(child)
        w.hide()
        w.setParent(None)
        self.children.pop(idx)
        return True

    def index_of(self, child: SplitChild) -> int:
        """获取子节点在 children 中的索引。"""
        try:
            return self.children.index(child)
        except ValueError:
            return -1


class LayoutTree:
    """布局树：根为 SplitNode，叶子为 PaneWidget。支持 split、remove_pane、折叠单子 SplitNode。"""

    def __init__(
        self,
        root: SplitNode,
        style_splitter: Callable[[QSplitter], None] | None = None,
        on_root_replaced: Callable[[SplitNode, SplitNode], None] | None = None,
    ):
        self._root = root
        self._pane_to_parent: dict[PaneWidget, SplitNode] = {}#每个panewidget有一个唯一父节点
        self._pane_id_to_widget: dict[str, PaneWidget] = {}
        self._style_splitter = style_splitter
        self._on_root_replaced = on_root_replaced

    def root(self) -> SplitNode:
        return self._root

    def dump_tree(self) -> list[str]:
        """返回当前布局树的多行文本描述，便于调试与断言。"""
        return _dump_node(self._root)

    def print_tree(self) -> None:
        """打印当前布局树信息到控制台。"""
        for line in self.dump_tree():
            print(line)
        print("---")

    def find_parent_of_pane(self, pane: PaneWidget) -> SplitNode | None:
        """查找 pane 的父 SplitNode。"""
        return self._pane_to_parent.get(pane)

    def register_pane_parent(self, pane: PaneWidget, parent: SplitNode) -> None:
        self._pane_to_parent[pane] = parent
        self._pane_id_to_widget[pane.pane_id] = pane

    def unregister_pane(self, pane: PaneWidget) -> None:
        self._pane_to_parent.pop(pane, None)
        self._pane_id_to_widget.pop(pane.pane_id, None)

    def find_pane_by_id(self, pane_id: str) -> PaneWidget | None:
        return self._pane_id_to_widget.get(pane_id)

    def panes(self) -> list[PaneWidget]:
        """返回所有已注册的 pane（返回副本，可安全迭代或修改）。"""
        return list(self._pane_id_to_widget.values())

    def get_default_target_pane(self) -> PaneWidget | None:
        """返回当前默认目标窗格（用于添加新内容）；无窗格时返回 None。"""
        panes_list = self.panes()
        return panes_list[0] if panes_list else None

    def add_pane_to_root(self, pane: PaneWidget) -> None:
        """将 pane 添加为根的唯一子（初始状态或根当前为空时使用）。"""
        self._root.add_child(pane)
        self.register_pane_parent(pane, self._root)

    def split(
        self,
        pane: PaneWidget,#被分裂的Panewidget
        direction: Qt.Orientation,
        insert_before: bool,
        new_pane: PaneWidget,#新建的panewidget
    ) -> None:
        """
        同方向时在父节点下插入新 pane 为兄弟（N-ary）；不同方向时新建 SplitNode，原 pane 与新 pane 为其二子。
        insert_before: True 表示新 pane 在原 pane 前/上，False 表示后/下。
        """
        parent = self.find_parent_of_pane(pane)
        if parent is None:#没有父节点，则pane是根节点
            if pane in self._root.children:
                parent = self._root
                self.register_pane_parent(pane, parent)
            else:
                return
        idx = parent.index_of(pane)
        if idx < 0:
            return

        # 根无方向时（仅单 pane）：用本次 direction 定型根，不进入同向/异向分支
        if parent is self._root and self._root.orientation is None:
            self._upgrade_root_to_split(direction, pane, insert_before, new_pane)
            return

        if parent.orientation == direction:
            # 同方向：在同一父下插入新 pane 为兄弟，不新建 SplitNode
            insert_idx = idx if insert_before else idx + 1
            parent.add_child(new_pane, insert_idx)
            self.register_pane_parent(new_pane, parent)
            parent.splitter.setSizes([9999] * len(parent.children))
        else:
            self._split_different_direction(
                parent, pane, idx, direction, insert_before, new_pane
            )

    def _split_different_direction(
        self,
        parent: SplitNode,
        pane: PaneWidget,
        idx: int,
        direction: Qt.Orientation,
        insert_before: bool,
        new_pane: PaneWidget,
    ) -> None:
        """不同方向时：新建 SplitNode，其下仅原 pane 与新 pane，插入到 parent 的 idx 位置。"""
        old_sizes = None
        if parent.orientation is not None and len(parent.children) >= 2:
            old_sizes = list(parent.splitter.sizes())
        new_split = SplitNode(direction)
        if self._style_splitter:
            self._style_splitter(new_split.splitter)
        parent.remove_child(pane)
        self.unregister_pane(pane)
        if insert_before:
            new_split.add_child(new_pane, 0)
            new_split.add_child(pane, 1)
        else:
            new_split.add_child(pane, 0)
            new_split.add_child(new_pane, 1)
        new_split.splitter.setSizes(EQUAL_SPLIT_SIZES)
        parent.children.insert(idx, new_split)
        parent.splitter.insertWidget(idx, new_split.splitter)
        new_split._parent_node = parent
        new_split._parent_splitter = parent.splitter
        self.register_pane_parent(pane, new_split)
        self.register_pane_parent(new_pane, new_split)
        if old_sizes is not None:
            parent.splitter.setSizes(old_sizes)


    def remove_pane(self, pane: PaneWidget) -> None:
        """删除 pane，若父 SplitNode 只剩 1 子则折叠（用剩余子替换自身）。"""
        parent = self.find_parent_of_pane(pane)
        if parent is None:
            return
        parent.remove_child(pane)
        self.unregister_pane(pane)
        pane.deleteLater()

        # 简化：若 parent 只剩 1 子，用该子替换 parent
        self._promote_single_child(parent)

    def _promote_single_child(self, node: SplitNode) -> None:
        """若 node 仅剩 1 子，用该子替换 node；若 node 是根则恢复为无方向单窗格。
        树的简化，提升子节点，去除中间的splitnode节点，使得树的结构更加简单
        """
        if len(node.children) != 1:
            return
        only_child = node.children[0]
        grandparent = node._parent_node

        if grandparent is None:
            # node 是根：仅一子时，子为 Pane 则无方向单窗格；子为 Split 则提升为根
            if isinstance(only_child, PaneWidget):
                # 根当前是「已定型」的 QSplitter（曾调用过 _upgrade_root_to_split）：恢复为无方向单窗格
                if node.orientation is not None and node._container is not None:
                    self._downgrade_root_to_single(node)
                    return
                # 根是纯 SplitNode（无 _container，例如从子节点提升上来的）：新建无方向根，移入唯一 pane 并替换根
                if node.orientation is not None and node._container is None:
                    new_root = SplitNode(None)
                    node.remove_child(only_child)
                    self.unregister_pane(only_child)
                    new_root.add_child(only_child)
                    self.register_pane_parent(only_child, new_root)
                    old_root = node
                    self._root = new_root
                    if self._on_root_replaced:
                        self._on_root_replaced(old_root, new_root)
                    old_root.children.clear()
                    if old_root._splitter is not None:
                        old_root._splitter.setParent(None)
                        old_root._splitter.deleteLater()
                        old_root._splitter = None
                    return
                return
            # only_child 为 SplitNode：提升为根，并通知上层替换根 widget
            old_root = node
            self._root = only_child
            only_child._parent_node = None
            only_child._parent_splitter = None
            if self._on_root_replaced:
                self._on_root_replaced(old_root, only_child)
            return

        # 从 grandparent 中移除 node，加入 only_child
        idx = grandparent.index_of(node)
        grandparent.remove_child(node)
        w = _widget_of(only_child)
        grandparent.children.insert(idx, only_child)
        grandparent.splitter.insertWidget(idx, w)
        if isinstance(only_child, PaneWidget):
            self.register_pane_parent(only_child, grandparent)
        else:
            only_child._parent_node = grandparent
            only_child._parent_splitter = grandparent.splitter
        # _pane_to_parent 只记录直接父节点，only_child 下的 Pane 仍指向 only_child，无需改

        # 递归检查 grandparent
        self._promote_single_child(grandparent)

    def _upgrade_root_to_split(
        self,
        direction: Qt.Orientation,
        pane: PaneWidget,
        insert_before: bool,
        new_pane: PaneWidget,
    ) -> None:
        """根从无方向单窗格变为带方向的 QSplitter，放入原 pane 与新 pane。
        Root (无方向, 单 Pane)
            ↓
        Root (有方向, QSplitter)
            ├── Pane A
            └── Pane B
        """
        root = self._root
        assert root._container is not None and root._splitter is None
        root.orientation = direction
        root._splitter = QSplitter(direction)
        if self._style_splitter:
            self._style_splitter(root._splitter)
        lay = root._container.layout()
        # 从 container 移除当前唯一的 pane（先取 widget 再 removeItem，避免 item 被删后访问）
        for i in range(lay.count()):
            item = lay.itemAt(i)
            if item and item.widget() is pane:
                lay.removeItem(item)
                break
        pane.setParent(None)
        # 必须先 addWidget 再 show，否则 pane 无父控件时 show() 会变成顶级窗口弹出
        if insert_before:
            root._splitter.addWidget(new_pane)
            root._splitter.addWidget(pane)
            root.children = [new_pane, pane]
        else:
            root._splitter.addWidget(pane)
            root._splitter.addWidget(new_pane)
            root.children = [pane, new_pane]
        pane.show()
        new_pane.show()
        root._splitter.setSizes(EQUAL_SPLIT_SIZES)
        lay.addWidget(root._splitter)
        self.register_pane_parent(pane, root)
        self.register_pane_parent(new_pane, root)


    def _downgrade_root_to_single(self, root: SplitNode) -> None:
        """根从带方向 QSplitter 恢复为无方向单窗格容器。
        当根只剩一个子时，把分裂根降级回单窗格根
        Root (有方向, QSplitter)
            ├── Pane A
            └── Pane B
            ↓
        Root (无方向, 单 Pane)
        """
        assert root._parent_node is None and len(root.children) == 1
        only_child = root.children[0]
        widget = _widget_of(only_child)
        lay = root._container.layout()
        # 移除 _splitter（先取引用再 removeItem，避免 item 被删后访问）
        splitter_w = root._splitter
        for i in range(lay.count()):
            item = lay.itemAt(i)
            if item and item.widget() is splitter_w:
                lay.removeItem(item)
                break
        splitter_w.setParent(None)
        splitter_w.deleteLater()
        root._splitter = None
        root.orientation = None
        lay.addWidget(widget)
        widget.show()
