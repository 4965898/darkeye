"""测试 layout_tree 中 SplitNode 与 LayoutTree 的正确性。"""
import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parents[3]  
sys.path.insert(0, str(root_dir))

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt

from ui.demo.layout_tree import SplitNode, LayoutTree
from ui.demo.pane_widget import PaneWidget


def _ensure_app():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


# -------- SplitNode 测试 --------


def test_split_node_add_child_pane():
    """SplitNode 添加 PaneWidget 子节点后，children 与 splitter 一致。"""
    _ensure_app()
    node = SplitNode(Qt.Horizontal)
    p1 = PaneWidget(pane_id="p1")
    p2 = PaneWidget(pane_id="p2")

    node.add_child(p1)
    assert len(node.children) == 1
    assert node.splitter.count() == 1
    assert node.splitter.widget(0) is p1

    node.add_child(p2)
    assert len(node.children) == 2
    assert node.splitter.count() == 2
    assert node.splitter.widget(1) is p2


def test_split_node_add_child_split_node():
    """SplitNode 添加子 SplitNode 时，splitter 里放的是子节点的 splitter。"""
    _ensure_app()
    parent = SplitNode(Qt.Horizontal)
    child_node = SplitNode(Qt.Vertical)
    p = PaneWidget(pane_id="leaf")

    child_node.add_child(p)
    parent.add_child(child_node)

    assert len(parent.children) == 1
    assert parent.children[0] is child_node
    assert parent.splitter.count() == 1
    assert parent.splitter.widget(0) is child_node.splitter
    assert child_node._parent_node is parent
    assert child_node._parent_splitter is parent.splitter


def test_split_node_add_child_at_index():
    """add_child(..., index=0) 插入到首位。"""
    _ensure_app()
    node = SplitNode(Qt.Horizontal)
    p1 = PaneWidget(pane_id="p1")
    p2 = PaneWidget(pane_id="p2")

    node.add_child(p1)
    node.add_child(p2, 0)

    assert node.children[0] is p2
    assert node.children[1] is p1
    assert node.splitter.widget(0) is p2
    assert node.splitter.widget(1) is p1


def test_split_node_index_of():
    """index_of 返回正确索引，不存在返回 -1。"""
    _ensure_app()
    node = SplitNode(Qt.Horizontal)
    p1 = PaneWidget(pane_id="p1")
    p2 = PaneWidget(pane_id="p2")
    node.add_child(p1)
    node.add_child(p2)

    assert node.index_of(p1) == 0
    assert node.index_of(p2) == 1
    assert node.index_of(PaneWidget(pane_id="other")) == -1


def test_split_node_remove_child():
    """remove_child 后 children 与 splitter 同步减少。"""
    _ensure_app()
    node = SplitNode(Qt.Horizontal)
    p1 = PaneWidget(pane_id="p1")
    p2 = PaneWidget(pane_id="p2")
    node.add_child(p1)
    node.add_child(p2)

    ok = node.remove_child(p1)
    assert ok is True
    assert len(node.children) == 1
    assert node.splitter.count() == 1
    assert node.children[0] is p2
    assert node.splitter.widget(0) is p2

    ok = node.remove_child(PaneWidget(pane_id="x"))
    assert ok is False


def test_split_node_remove_child_split_node():
    """remove_child 移除子 SplitNode 时正确。"""
    _ensure_app()
    parent = SplitNode(Qt.Horizontal)
    child = SplitNode(Qt.Vertical)
    p = PaneWidget(pane_id="p")
    child.add_child(p)
    parent.add_child(child)

    parent.remove_child(child)
    assert len(parent.children) == 0
    assert parent.splitter.count() == 0


# -------- LayoutTree 测试 --------


def test_layout_tree_register_find_pane():
    """register_pane_parent / unregister_pane / find_parent_of_pane / find_pane_by_id。"""
    _ensure_app()
    root = SplitNode(Qt.Horizontal)
    tree = LayoutTree(root)
    p1 = PaneWidget(pane_id="id-1")
    p2 = PaneWidget(pane_id="id-2")
    root.add_child(p1)
    root.add_child(p2)

    assert tree.find_parent_of_pane(p1) is None  # 未注册
    tree.register_pane_parent(p1, root)
    tree.register_pane_parent(p2, root)

    assert tree.find_parent_of_pane(p1) is root
    assert tree.find_parent_of_pane(p2) is root
    assert tree.find_pane_by_id("id-1") is p1
    assert tree.find_pane_by_id("id-2") is p2
    assert tree.find_pane_by_id("none") is None

    tree.unregister_pane(p1)
    assert tree.find_parent_of_pane(p1) is None
    assert tree.find_pane_by_id("id-1") is None
    assert tree.find_pane_by_id("id-2") is p2


def test_layout_tree_add_pane_to_root():
    """add_pane_to_root 将 pane 作为根的唯一子并注册；根无方向时 orientation 为 None。"""
    _ensure_app()
    root = SplitNode(None)
    tree = LayoutTree(root)
    p = PaneWidget(pane_id="root-pane")

    tree.add_pane_to_root(p)

    assert len(root.children) == 1
    assert root.children[0] is p
    assert root.orientation is None
    assert tree.find_parent_of_pane(p) is root
    assert tree.find_pane_by_id("root-pane") is p


def test_layout_tree_split_insert_before():
    """根无方向时第一次 split 确定根方向；insert_before=True 时新 pane 在原 pane 前/上。"""
    _ensure_app()
    root = SplitNode(None)
    tree = LayoutTree(root)
    p1 = PaneWidget(pane_id="p1")
    tree.add_pane_to_root(p1)

    p2 = PaneWidget(pane_id="p2")
    tree.split(p1, Qt.Horizontal, insert_before=True, new_pane=p2)

    assert root.orientation == Qt.Horizontal
    assert len(root.children) == 2
    assert root.children[0] is p2
    assert root.children[1] is p1
    assert tree.find_parent_of_pane(p1) is root
    assert tree.find_parent_of_pane(p2) is root
    assert tree.find_pane_by_id("p1") is p1
    assert tree.find_pane_by_id("p2") is p2


def test_layout_tree_split_insert_after():
    """根无方向时第一次 split(Vertical) 使根定型为 Vertical；insert_before=False 时新 pane 在后/下。"""
    _ensure_app()
    root = SplitNode(None)
    tree = LayoutTree(root)
    p1 = PaneWidget(pane_id="p1")
    tree.add_pane_to_root(p1)

    p2 = PaneWidget(pane_id="p2")
    tree.split(p1, Qt.Vertical, insert_before=False, new_pane=p2)

    assert root.orientation == Qt.Vertical
    assert len(root.children) == 2
    assert root.children[0] is p1
    assert root.children[1] is p2
    assert tree.find_parent_of_pane(p1) is root
    assert tree.find_parent_of_pane(p2) is root


def test_layout_tree_remove_pane_collapse():
    """remove_pane 后若根只剩 1 子，应恢复为无方向单窗格。"""
    _ensure_app()
    root = SplitNode(None)
    tree = LayoutTree(root)
    p1 = PaneWidget(pane_id="p1")
    p2 = PaneWidget(pane_id="p2")
    tree.add_pane_to_root(p1)
    tree.split(p1, Qt.Horizontal, insert_before=False, new_pane=p2)

    tree.remove_pane(p2)

    assert len(root.children) == 1
    assert root.children[0] is p1
    assert root.orientation is None
    assert tree.find_parent_of_pane(p1) is root
    assert tree.find_pane_by_id("p1") is p1
    assert tree.find_pane_by_id("p2") is None


def test_layout_tree_remove_pane_no_collapse():
    """remove_pane 后若父仍有 2+ 子，不折叠。"""
    _ensure_app()
    root = SplitNode(None)
    tree = LayoutTree(root)
    p1 = PaneWidget(pane_id="p1")
    p2 = PaneWidget(pane_id="p2")
    p3 = PaneWidget(pane_id="p3")
    tree.add_pane_to_root(p1)
    tree.split(p1, Qt.Horizontal, insert_before=False, new_pane=p2)
    tree.split(p2, Qt.Horizontal, insert_before=False, new_pane=p3)

    tree.remove_pane(p3)

    assert root.orientation == Qt.Horizontal
    assert len(root.children) == 2
    assert root.children[0] is p1
    assert root.children[1] is p2
    assert tree.find_parent_of_pane(p1) is root
    assert tree.find_parent_of_pane(p2) is root


def test_layout_tree_remove_pane_promote_root():
    """根为 Split(V)，下挂 Split(H)+Pane(p3)，删除 p3 后应提升 Split(H) 为根，无 Split(—) 中间层。"""
    _ensure_app()
    root = SplitNode(None)
    tree = LayoutTree(root)
    p3 = PaneWidget(pane_id="p3")
    tree.add_pane_to_root(p3)
    p2 = PaneWidget(pane_id="p2")
    tree.split(p3, Qt.Vertical, insert_before=True, new_pane=p2)
    p4 = PaneWidget(pane_id="p4")
    tree.split(p2, Qt.Horizontal, insert_before=False, new_pane=p4)
    # 结构: Split(V) -> [Split(H)[p2, p4], Pane(p3)]

    tree.remove_pane(p3)

    new_root = tree.root()
    assert new_root.orientation == Qt.Horizontal, "新根应为 Split(H)"
    assert new_root._parent_node is None
    assert len(new_root.children) == 2
    assert new_root.children[0] is p2 and new_root.children[1] is p4
    assert tree.find_parent_of_pane(p2) is new_root
    assert tree.find_parent_of_pane(p4) is new_root
    assert tree.find_pane_by_id("p3") is None


def test_layout_tree_split_uses_registered_parent():
    """split 时若 pane 在根下但未注册，应能通过 root.children 找到并注册后继续。"""
    _ensure_app()
    root = SplitNode(None)
    tree = LayoutTree(root)
    p1 = PaneWidget(pane_id="p1")
    root.add_child(p1)
    # 不调用 register_pane_parent，模拟根直接子未注册的情况

    p2 = PaneWidget(pane_id="p2")
    tree.split(p1, Qt.Horizontal, insert_before=True, new_pane=p2)

    assert root.orientation == Qt.Horizontal
    assert len(root.children) == 2
    assert root.children[0] is p2
    assert root.children[1] is p1
    assert tree.find_parent_of_pane(p1) is root
    assert tree.find_parent_of_pane(p2) is root


# -------- PaneWidget 在树中的显示测试 --------


def test_pane_widget_in_splitter_parent_and_index():
    """PaneWidget 加入 SplitNode 后，父为 splitter、在 splitter 中的索引正确。"""
    _ensure_app()
    node = SplitNode(Qt.Horizontal)
    p1 = PaneWidget(pane_id="p1")
    p2 = PaneWidget(pane_id="p2")

    node.add_child(p1)
    assert p1.parent() is node.splitter
    assert node.splitter.indexOf(p1) == 0
    assert node.splitter.widget(0) is p1

    node.add_child(p2)
    assert p2.parent() is node.splitter
    assert node.splitter.indexOf(p2) == 1
    assert node.splitter.widget(1) is p2


def test_layout_tree_pane_displayed_in_window():
    """LayoutTree 的根作为窗口 centralWidget 时，add_pane_to_root 的 PaneWidget 显示正确。"""
    _ensure_app()
    from PySide6.QtWidgets import QMainWindow

    root = SplitNode(None)
    tree = LayoutTree(root)
    p = PaneWidget(pane_id="display-test")
    tree.add_pane_to_root(p)

    win = QMainWindow()
    win.setCentralWidget(root.root_widget())
    win.resize(400, 300)
    win.show()
    QApplication.processEvents()

    assert p.parent() is root.root_widget()
    assert len(root.children) == 1 and root.children[0] is p
    assert p.isVisible()
    assert p.size().width() > 0 and p.size().height() > 0, "PaneWidget 应有有效尺寸以便显示"


def test_layout_tree_split_panes_displayed_in_window():
    """split 后两个 PaneWidget 均在窗口中正确显示（可见且有尺寸）。"""
    _ensure_app()
    from PySide6.QtWidgets import QMainWindow

    root = SplitNode(None)
    tree = LayoutTree(root)
    p1 = PaneWidget(pane_id="p1")
    tree.add_pane_to_root(p1)
    p2 = PaneWidget(pane_id="p2")
    tree.split(p1, Qt.Horizontal, insert_before=False, new_pane=p2)

    win = QMainWindow()
    win.setCentralWidget(root.root_widget())
    win.resize(500, 300)
    win.show()
    QApplication.processEvents()

    for pane in (p1, p2):
        assert pane.isVisible(), f"PaneWidget {pane.pane_id} 应可见"
        assert pane.size().width() > 0 and pane.size().height() > 0, f"PaneWidget {pane.pane_id} 应有有效尺寸"


def run_manual():
    """命令行运行：执行所有测试并打印结果。"""
    _ensure_app()
    import sys
    mod = sys.modules[__name__]
    tests = [getattr(mod, n) for n in dir(mod) if n.startswith("test_") and callable(getattr(mod, n))]
    failed = []
    for t in tests:
        try:
            t()
            print(f"  OK  {t.__name__}")
        except Exception as e:
            failed.append((t.__name__, e))
            print(f"  FAIL {t.__name__}: {e}")
    if failed:
        print(f"\n失败: {len(failed)}/{len(tests)}")
        return 1
    print(f"\n全部通过: {len(tests)}")
    return 0


if __name__ == "__main__":
    sys.exit(run_manual())
