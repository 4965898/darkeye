import sys,os
from pathlib import Path
import logging

#----------------------------------------------------------
root_dir = Path(__file__).resolve().parents[2]  # 上两级
sys.path.insert(0, str(root_dir))

import networkx as nx
from PySide6.QtWidgets import QApplication, QMainWindow,QVBoxLayout, QWidget
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt,QSize

from core.graph.graph_session import GraphViewSession

import os
from pathlib import Path
import PySide6

qt_bin = Path(PySide6.__file__).resolve().parent


if hasattr(os, "add_dll_directory"):
    os.add_dll_directory(str(qt_bin))

from cpp_bindings.forced_direct_view.PyForceView import ForceViewOpenGL



from core.graph.graph_session import GraphViewSession
from core.graph.graph_filter import PassThroughFilter, EgoFilter
from core.graph.ForceViewSettingsPanel import ForceViewSettingsPanel
import random
import math


class ForceDirectedViewWidget(QWidget):
    '''控制面板+view的容器'''
    def __init__(self, parent=None):
        super().__init__(parent)

        self.init_ui()
        self.signal_connect()


    def init_ui(self):
        mainlayout = QVBoxLayout(self)

        self.container = QWidget(self)
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        mainlayout.addWidget(self.container)

        self.view = ForceViewOpenGL(parent=self.container)
        #self.view = ForceView(parent=self.container)


        self.container_layout.addWidget(self.view)

        # -------- Session：GraphManager -> 过滤 -> OpenGL View --------
        self.session = GraphViewSession()
        self.session.data_ready.connect(self._on_graph_data_ready)

        from ui.basic import IconPushButton
        self.settings_button = IconPushButton(iconpath="settings.svg", color="#5C5C5C", parent=self)

        self.panel = ForceViewSettingsPanel(self)

        self.settings_button.raise_()
        self.panel.raise_()

    
    
    def signal_connect(self):
        self.settings_button.clicked.connect(self._toggle_panel)



        # View -> 业务逻辑
        self.view.nodeLeftClicked.connect(self._on_node_clicked)

        self.panel.manyBodyStrengthChanged.connect(self.view.setManyBodyStrength)
        self.panel.centerStrengthChanged.connect(self.view.setCenterStrength)
        self.panel.linkStrengthChanged.connect(self.view.setLinkStrength)
        self.panel.linkDistanceChanged.connect(self.view.setLinkDistance)

        self.panel.radiusFactorChanged.connect(self.view.setRadiusFactor)
        self.panel.linkwidthFactorChanged.connect(self.view.setSideWidthFactor)
        self.panel.textThresholdFactorChanged.connect(self.view.setTextThresholdFactor)

        self.panel.restartRequested.connect(self.view.restartSimulation)
        self.panel.pauseRequested.connect(self.view.pauseSimulation)
        self.panel.resumeRequested.connect(self.view.resumeSimulation)
        self.panel.fitInViewRequested.connect( self.view.fitViewToContent)



        self.panel.addNodeRequested.connect(self.addnodetest)
        self.panel.removeNodeRequested.connect(self.removenodetest)
        self.panel.addEdgeRequested.connect(self.addedgetest)
        self.panel.removeEdgeRequested.connect(self.removeedgetest)

        self.panel.graphModeChanged.connect(self._switch_graph)
        self.panel.contentSizeChanged.connect(self._update_panel_geometry)


        # View -> panel (update labels)
        self.view.fpsUpdated.connect(self.panel.setFps)
        self.view.tickTimeUpdated.connect(self.panel.setTickTime)
        self.view.paintTimeUpdated.connect(self.panel.setPaintTime)
        self.view.scaleChanged.connect(self.panel.setscale)
        self.view.alphaUpdated.connect(self.panel.setalpha)
  


    def addnodetest(self):
        self.view.add_node_runtime("c200",10.0,10.0,"c200",7.0,QColor("#5C5C5C"))
        self.view.add_node_runtime("c201",0.0,0.0,"c201",7.0,QColor("#257845"))


    def removenodetest(self):
        self.view.remove_node_runtime("c200")
    
    def addedgetest(self):
        self.view.add_edge_runtime("c200","c201")

    def removeedgetest(self):
        self.view.remove_edge_runtime("c200","c201")


    def _on_node_clicked(self, node_id: str) -> None:
        """
        节点点击后的跳转逻辑（node_id 为节点 id，来自 m_ids[index]）：
        - a 开头：跳转 single_actress
        - w 开头：跳转 work
        """
        if not node_id:
            return
        nodename = str(node_id)

        if nodename.startswith("a"):
            from ui.navigation.router import Router
            Router.instance().push("single_actress", actress_id=int(nodename[1:]))
            print(f"跳转女优界面：{nodename}")
        elif nodename.startswith("w"):
            from ui.navigation.router import Router
            Router.instance().push("work", work_id=int(nodename[1:]))
            print(f"跳转作品界面：{nodename}")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_panel_geometry()

    def _update_panel_geometry(self) -> None:
        rect = self.rect()
        if rect.isEmpty():
            return
        margin = 10
        offset_x = 30
        offset_y = 30
        btn_size: QSize = self.settings_button.sizeHint()
        self.settings_button.move(
            max(margin, rect.width() - btn_size.width() - margin - offset_x),
            margin + offset_y,
        )
        if self.panel.isVisible():
            panel_width: int = min(250, max(0, rect.width() - 2 * margin))
            panel_height: int = self.panel.sizeHint().height()
            self.panel.resize(panel_width, panel_height)
            self.panel.move(
                max(margin, rect.width() - panel_width - margin-offset_x),
                btn_size.height() + 2 * margin+offset_y,
            )
            self.panel.raise_()
            self.settings_button.raise_()

    def _toggle_panel(self):
        if self.panel.isVisible():
            self.panel.setVisible(False)
        else:
            self.panel.setVisible(True)
            self.panel.adjustSize()
            self._update_panel_geometry()
            self.panel.raise_()
            self.settings_button.raise_()
        
    def _switch_graph(self, mode: str):
        """
        切换图类型：
        - all: 使用 PassThroughFilter，全图
        - favorite: 使用 EgoFilter 或你自定义的“片关系图”过滤器
        - test: 使用随机图（不经过 GraphManager）
        """
        if mode == "test":
            # 测试模式：直接生成一张随机小图，不走 GraphManager / Session
            G = nx.gnm_random_graph(200, 400)
            # 这里你也可以给节点加 label/group 属性
            for n in G.nodes():
                G.nodes[n]["label"] = f"n{n}"
            self._set_graph_from_networkx(G, modify=False)
            return

        # 其他模式走 GraphViewSession + GraphManager
        if mode == "all":
            self.session.set_filter(PassThroughFilter())
        elif mode == "favorite":
            # 示例：以某个中心点的 ego 图作为“片关系图”
            # center_id 你可以改成当前选中的作品/女优，比如 "a100" / "w123"
            center_id = "a100"
            self.session.set_filter(EgoFilter(center_id=center_id, radius=2))
        else:
            self.session.set_filter(PassThroughFilter())

        # 触发一次重载
        self.session.reload()

    def load_graph(self,G):
        pass
        #self.view.load_graph(G)

    def _set_graph_from_networkx(self, G: nx.Graph, modify: bool = False) -> None:
        """
        把一个 networkx.Graph 转成 ForceView/ForceViewOpenGL.setGraph 所需的参数。
        """
        if G is None:
            return

        nodes = list(G.nodes())
        n = len(nodes)
        if n == 0:
            return

        index_of = {node_id: i for i, node_id in enumerate(nodes)}

        # 1. edges: 扁平化 [src0, dst0, src1, dst1, ...]，用“索引”即可
        edges: list[int] = []
        for u, v in G.edges():
            iu = index_of[u]
            iv = index_of[v]
            edges.append(iu)
            edges.append(iv)
        pos: list[float] = []



        # 3. ids / labels / radii
        # ids: 传给 C++ 的是字符串列表（与 labels 同类型）；C++ 点击时发出m_id[下标]
        # nx 节点 id 就是 nodes[i]（女优 "a"+数字，作品 "w"+数字），已保存在 self._nodes 里。
        ids: list[str] = []
        labels: list[str] = []
        radii: list[float] = []

        degrees = dict(G.degree())
        deg_values = list(degrees.values()) or [1]
        min_deg = min(deg_values)
        max_deg = max(deg_values)

        for i, node_id in enumerate(nodes):
            # node_id 即 nx 图节点 id（如 "a100"/"w123"）；C++ 接收 QStringList，传 str(node_id)。
            ids.append(str(node_id))

            data = G.nodes[node_id]
            label = data.get("label", str(node_id))#label就是节点的标签，女优是姓名，作品是番号名
            labels.append(str(label))

            deg = float(degrees.get(node_id, 1))
            # 度数重映射到半径 [4, 10]
            if max_deg <= min_deg:
                r = 7.0  # 全部同度数时取中间值
            else:
                t = (deg - min_deg) / (max_deg - min_deg)
                r = 4.0 + t * 6.0
            radii.append(r)

        # 4. 颜色（可选：这里统一灰色，后面你可以按 group 分颜色）
        from PySide6.QtGui import QColor
        node_colors = [QColor("#5C5C5C")] * n
        logging.info(G)

        # 保存节点和 label，供点击跳转使用
        self._nodes = nodes
        self._labels = labels

        # 5. 调用 C++ 视图（用位置参数，避免关键字 id 与 Python 内置 id 冲突导致 Shiboken 绑定异常）
        self.view.setGraph(n, edges, pos, ids, labels, radii, node_colors)

    def _on_graph_data_ready(self, payload: dict) -> None:
        """
        Session -> View：收到过滤后的子图，调用 setGraph。
        """
        cmd = payload.get("cmd")
        if cmd != "load_graph":
            return

        G = payload.get("graph")
        if G is None:
            return

        

        modify = bool(payload.get("modify", False))
        self._set_graph_from_networkx(G, modify=modify)
        

def main():
    from core.graph.graph_filter import EgoFilter
    from core.graph.graph_manager import GraphManager

    app = QApplication(sys.argv)

    # 1. 显式初始化 GraphManager（异步，后台线程加载图）
    manager = GraphManager.instance()
    if not manager._initialized:
        manager.initialize()

    window = QMainWindow()
    window.setWindowTitle("ForceView - Ego Graph (Actress ID 100)")
    window.resize(1000, 700)

    central_widget = ForceDirectedViewWidget()
    window.setCentralWidget(central_widget)
    view_session = central_widget.session

    # 2. 等图加载完成后再设置过滤器并加载视图（否则 reload() 时 G 仍为空）
    def on_graph_ready():
        #view_session.set_filter(EgoFilter(center_id="a100", radius=3))
        view_session.reload()

    if manager._initialized:
        on_graph_ready()
    else:
        manager.initialization_finished.connect(on_graph_ready)

    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

