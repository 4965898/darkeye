import sys, random, math
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsSimpleTextItem
)
from PySide6.QtGui import QBrush, QPen, QColor, QPainter
from PySide6.QtCore import Qt, QTimer
import networkx as nx


class GraphNode(QGraphicsEllipseItem):
    """可拖动节点"""
    def __init__(self, node_id, x, y, radius=15, label=None):
        super().__init__(-radius, -radius, radius * 2, radius * 2)
        self.node_id = node_id
        self.label = label
        self._connected_edges = []  # ✅ 必须在 setPos 之前定义

        # ---- 物理参数 ----
        self.vx = 0.0  # 水平速度
        self.vy = 0.0  # 垂直速度

        self.setBrush(QBrush(QColor("#66ccff")))
        self.setPen(QPen(Qt.black, 1))
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)
        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges, True)
        self.setPos(x, y)

        if label:
            text = QGraphicsSimpleTextItem(label, self)
            text.setPos(-radius, radius + 2)

    def add_edge(self, edge):
        self._connected_edges.append(edge)

    def itemChange(self, change, value):
        if change == QGraphicsEllipseItem.ItemPositionHasChanged:
            if hasattr(self, "_connected_edges"):
                for edge in self._connected_edges:
                    edge.update_position()
        return super().itemChange(change, value)


class GraphEdge(QGraphicsLineItem):
    def __init__(self, node1: GraphNode, node2: GraphNode):
        super().__init__()
        self.node1 = node1
        self.node2 = node2
        self.setPen(QPen(Qt.gray, 1))
        node1.add_edge(self)
        node2.add_edge(self)
        self.setZValue(-1)
        self.update_position()

    def update_position(self):
        p1 = self.node1.scenePos()
        p2 = self.node2.scenePos()
        self.setLine(p1.x(), p1.y(), p2.x(), p2.y())




class ForceDirectedView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.myscene = QGraphicsScene(self)
        self.setScene(self.myscene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.scale_factor = 1.0
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        # ---- 创建 NetworkX 图 ----
        #G = nx.fast_gnp_random_graph(200, 0.02)
        G = self.generate_graph()

        pos = nx.spring_layout(G, k=0.8, iterations=50)

        # ---- 创建节点与边 ----
        self.node_items = {}
        scale = 300
        for n, (x, y) in pos.items():
            data = G.nodes[n]
            label = data.get("label", str(n))  # 优先使用图中保存的 label
            node = GraphNode(n, x * scale, y * scale, label=label)
            self.myscene.addItem(node)
            self.node_items[n] = node

        for u, v in G.edges:
            edge = GraphEdge(self.node_items[u], self.node_items[v])
            self.myscene.addItem(edge)

        self.edges = [e for e in self.myscene.items() if isinstance(e, GraphEdge)]

        # ---- 启动画动画 ----
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_forces)
        self.timer.start(30)  # 每 60ms 更新一帧

    def generate_graph(self)->nx.graph:
        '''产生无向图'''
        
        from core.database.connection import get_connection
        from config import DATABASE
        conn=get_connection(DATABASE,True)
        cursor = conn.cursor()

        q1="""
SELECT 
	actress_id,
	(SELECT cn FROM actress_name WHERE actress_id=actress.actress_id)AS name
FROM
	actress
"""
        cursor.execute(q1)
        actresses = cursor.fetchall()
        q2="""
SELECT 
	work_id,
	serial_number
FROM
	work
"""
        cursor.execute(q2)
        works = cursor.fetchall()

        cursor.execute("SELECT work_id, actress_id FROM work_actress_relation")
        relations = cursor.fetchall()

        cursor.close()
        conn.close()

        #添加图
        G=nx.Graph()
                # 添加女优节点
        for aid, name in actresses:
            G.add_node(
                f"a{aid}",  # 避免与作品 id 冲突
                label=name,
                title=f"女优: {name}",
                group="actress",
                color="#ff99cc"
            )
                    # 添加作品节点
        for wid, title in works:
            G.add_node(
                f"w{wid}",
                label=title,
                title=f"作品: {title}",
                group="work",
                color="#99ccff",
                shape="box"
            )

        # 添加边（参演关系）
        for wid, aid in relations:
            G.add_edge(f"a{aid}", f"w{wid}")
        return G

    def update_forces(self):
        """计算力导向物理模拟"""
        center_x, center_y = 0, 0  # 场景中心
        k_center = 0.01           # 中心吸引系数

        k_repulsion = 50    # 斥力常数
        k_spring = 0.02        # 弹簧系数
        damping = 0.85         # 阻尼
        dt = 0.3               # 时间步长

        nodes:list[GraphNode] = list(self.node_items.values())

        # 初始化力
        forces = {n: [0.0, 0.0] for n in nodes}

        max_repulsion_dist2 = 400**2  # 超过500像素的节点不计算斥力
        # --- 计算斥力 ---
        for i, n1 in enumerate(nodes):#两两历遍，计算斥力
            for n2 in nodes[i+1:]:
                dx = n1.x() - n2.x()
                dy = n1.y() - n2.y()
                dist2 = dx*dx + dy*dy + 0.01
                if dist2 > max_repulsion_dist2:
                    continue  # 太远，忽略
                force = k_repulsion / dist2#越远，斥力越小
                fx = force * dx #计算所受到的分力
                fy = force * dy
                forces[n1][0] += fx#计算每个节点所受到的力
                forces[n1][1] += fy
                forces[n2][0] -= fx
                forces[n2][1] -= fy

        # --- 计算吸引力（边） ---
        for edge in self.edges:
            n1, n2 = edge.node1, edge.node2
            dx = n2.x() - n1.x()
            dy = n2.y() - n1.y()
            dist = math.hypot(dx, dy) + 0.01
            force = k_spring * (dist - 100)  # 理想弹簧长度=100
            fx = force * dx / dist
            fy = force * dy / dist
            forces[n1][0] += fx
            forces[n1][1] += fy
            forces[n2][0] -= fx
            forces[n2][1] -= fy

        #所有点都有一个向心力
        for n in nodes:
            dx = center_x - n.x()
            dy = center_y - n.y()
            forces[n][0] += dx * k_center
            forces[n][1] += dy * k_center

        # --- 更新位置 ---
        for n in nodes:
            n.vx = (n.vx + forces[n][0] * dt) * damping
            n.vy = (n.vy + forces[n][1] * dt) * damping
            n.setPos(n.x() + n.vx * dt, n.y() + n.vy * dt)
        
        # --- 当平均速率低时停止迭代计算 ---
        total_speed = 0.0  # ✅ 用于计算平均速度
        for n in nodes:
            n.vx = (n.vx + forces[n][0] * dt) * damping
            n.vy = (n.vy + forces[n][1] * dt) * damping
            n.setPos(n.x() + n.vx * dt, n.y() + n.vy * dt)
            total_speed += abs(n.vx) + abs(n.vy)

        avg_speed = total_speed / len(nodes)

        # ✅ 当速度足够小，说明系统收敛，停止动画
        if avg_speed < 0.05:
            print(f"布局稳定，平均速度 {avg_speed:.4f}，停止模拟。")
            self.timer.stop()
        self.update_scene_rect()

    def wheelEvent(self, event):
        zoom_in = event.angleDelta().y() > 0
        factor = 1.15 if zoom_in else 1 / 1.15
        new_scale = self.scale_factor * factor
        if 0.1 < new_scale < 10:
            self.scale(factor, factor)
            self.scale_factor = new_scale
        event.accept()  # 阻止事件向上传递

    def update_scene_rect(self):
        rect = self.myscene.itemsBoundingRect()
        rect.adjust(-100, -100, 100, 100)  # 增加一点边距
        self.myscene.setSceneRect(rect)