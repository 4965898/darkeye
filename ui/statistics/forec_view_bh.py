# force_view_bh.py
import sys
import math
import random
from typing import List, Dict, Tuple, Optional

import networkx as nx
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsSimpleTextItem, QPushButton, QVBoxLayout, QWidget,QGraphicsRectItem
)
from PySide6.QtGui import QBrush, QPen, QColor, QPainter
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF

# ------------------------------
# QGraphics items for node/edge
# ------------------------------
class GraphNode(QGraphicsEllipseItem):
    '''绘图显示交互节点类，带的信息尽量的少'''
    def __init__(self, node_id, x, y, radius=8, label=None):
        super().__init__(-radius, -radius, radius*2, radius*2)
        self.node_id = node_id
        self._connected_edges:list[GraphEdge] = []

        self.setPos(x, y)
        self.setBrush(QBrush(QColor("#66ccff")))
        self.setPen(QPen(Qt.black, 0.5))
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)
        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges, True)

        self._label_item = None
        if label:
            self._label_item = QGraphicsSimpleTextItem(label, self)
            self._label_item.setPos(radius + 2, -radius - 2)

        # physics
        self.vx = 0.0
        self.vy = 0.0
        self.mass = 1.0

    def add_edge(self, edge):
        self._connected_edges.append(edge)

    def itemChange(self, change, value):
        if change == QGraphicsEllipseItem.ItemPositionHasChanged:
            for e in self._connected_edges:
                e.update_position()
        return super().itemChange(change, value)

    def set_label(self, text: str):
        if self._label_item is None:
            self._label_item = QGraphicsSimpleTextItem(text, self)
        else:
            self._label_item.setText(text)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        self.setSelected(False)  # 释放时立即取消选中


class GraphEdge(QGraphicsLineItem):
    '''绘图显示交互边类，带的信息尽量少'''
    def __init__(self, node1: GraphNode, node2: GraphNode):
        super().__init__()
        self.node1 = node1
        self.node2 = node2
        self.setPen(QPen(Qt.gray, 0.7))
        node1.add_edge(self)
        node2.add_edge(self)
        self.setZValue(-1)
        self.update_position()

    def update_position(self):
        p1 = self.node1.scenePos()
        p2 = self.node2.scenePos()
        self.setLine(p1.x(), p1.y(), p2.x(), p2.y())


# ------------------------------
# Barnes-Hut Quadtree
# ------------------------------
class QuadTree:
    """Simple Barnes-Hut quadtree for 2D points.

    Each leaf holds either 0 or 1 particle. Internal nodes keep center-of-mass.
    """
    def __init__(self, bbox: QRectF):
        self.bbox = bbox  # QRectF(x, y, w, h)
        self.center_of_mass = QPointF(0, 0)
        self.total_mass = 0.0
        self.particle: Optional[GraphNode] = None
        self.children = None  # NW, NE, SW, SE

    def is_leaf(self):
        return self.children is None

    def insert(self, p: GraphNode):
        '''将一个点插入树中'''
        x, y = p.x(), p.y()
        # if empty leaf -> store particle
        if self.is_leaf() and self.particle is None:#直接放入
            self.particle = p
            self.center_of_mass = QPointF(x * p.mass, y * p.mass)#不必除以质总质量算坐标finalize会统一计算
            self.total_mass = p.mass
            return

        # if leaf and has a particle -> subdivide
        if self.is_leaf():#无叶子，分裂，将现有的插入子树中
            existing = self.particle#记录原有的粒子
            self._subdivide()
            # re-insert existing
            self._put_into_child(existing)
            self.particle = None

        #有子树
        # put new particle into child
        self._put_into_child(p)

        # update center of mass and total mass
        self.total_mass += p.mass
        # center_of_mass stored as sum(m*x), will normalize when needed
        self.center_of_mass = QPointF(self.center_of_mass.x() + x * p.mass,
                                      self.center_of_mass.y() + y * p.mass)

    def _subdivide(self):
        x, y, w, h = self.bbox.x(), self.bbox.y(), self.bbox.width(), self.bbox.height()
        hw, hh = w / 2.0, h / 2.0
        self.children = [
            QuadTree(QRectF(x, y, hw, hh)),             # NW
            QuadTree(QRectF(x + hw, y, hw, hh)),        # NE
            QuadTree(QRectF(x, y + hh, hw, hh)),        # SW
            QuadTree(QRectF(x + hw, y + hh, hw, hh)),   # SE
        ]
        # if previously had a center_of_mass, keep it as sum(m*x) etc.
        # total_mass is already set for that particle.
        # (we moved the particle out, total_mass will be recomputed during insert)
        # Reset ours: will be recomputed when children insertions update it.
        self.total_mass = 0.0
        self.center_of_mass = QPointF(0.0, 0.0)

    def _put_into_child(self, p: GraphNode):
        x, y = p.x(), p.y()
        for child in self.children:
            if child.bbox.contains(QPointF(x, y)):
                child.insert(p)
                # update our aggregated totals from child
                # (we'll aggregate later in higher callers)
                self.total_mass += p.mass
                self.center_of_mass = QPointF(self.center_of_mass.x() + x * p.mass,
                                                            self.center_of_mass.y() + y * p.mass)
                return
        # If none child contains it (edge cases), put into nearest child
        nearest = min(self.children, key=lambda c: _dist_point_rect(x, y, c.bbox))
        nearest.insert(p)
        self.total_mass += p.mass
        self.center_of_mass = QPointF(self.center_of_mass.x() + x * p.mass,
                                                            self.center_of_mass.y() + y * p.mass)

    def finalize(self):
        """Normalize center_of_mass to true coordinates (divide by total_mass).
           And propagate finalize to children if exists.
           统一计算其质量，将质量算对
        """
        if self.is_leaf():#是叶子而且有质量
            if self.total_mass > 0:
                # if we stored sum(m*x), normalize
                self.center_of_mass = QPointF(self.center_of_mass.x() / self.total_mass,
                                              self.center_of_mass.y() / self.total_mass)
        else:
            # finalize children first
            self.total_mass = 0.0
            self.center_of_mass = QPointF(0.0, 0.0)
            for c in self.children:
                c.finalize()
                if c.total_mass > 0:
                    self.center_of_mass = QPointF(self.center_of_mass.x() + c.center_of_mass.x() * c.total_mass,
                                                  self.center_of_mass.y() + c.center_of_mass.y() * c.total_mass)
                    self.total_mass += c.total_mass
            if self.total_mass > 0:
                self.center_of_mass = QPointF(self.center_of_mass.x() / self.total_mass,
                                              self.center_of_mass.y() / self.total_mass)

    def find_nearby_nodes(self, node: GraphNode, radius: float, result: list):
        """查找指定节点半径范围内的所有其他节点（四叉树优化）"""
        if self.total_mass == 0:
            return
        
        px, py = node.x(), node.y()
        
        # 计算当前节点与查询节点的距离
        dx = self.center_of_mass.x() - px
        dy = self.center_of_mass.y() - py
        dist = math.hypot(dx, dy)
        
        # 计算当前节点的边界尺寸
        s = max(self.bbox.width(), self.bbox.height())
        
        # 如果当前节点足够远或者足够小，检查是否可以批量处理
        if s / (dist + 1e-6) < 0.5 or self.is_leaf():
            # 如果是叶子节点且有粒子，且不是查询节点自身
            if self.is_leaf() and self.particle and self.particle is not node:
                # 检查实际距离
                node_dx = self.particle.x() - px
                node_dy = self.particle.y() - py
                node_dist = math.hypot(node_dx, node_dy)
                if node_dist < radius:
                    result.append(self.particle)
            # 如果是内部节点，递归检查所有子节点
            elif not self.is_leaf():
                for child in self.children:
                    child.find_nearby_nodes(node, radius, result)
        else:
            # 需要进一步细分检查
            if self.children:
                for child in self.children:
                    child.find_nearby_nodes(node, radius, result)


    def compute_force_on(self, p: GraphNode, theta: float, repulsion: float) -> Tuple[float, float]:
        """Compute approximate repulsive force on particle p from this subtree."""
        distance_max=500
        # If node is empty
        if self.total_mass == 0:
            return 0.0, 0.0

        px, py = p.x(), p.y()
        # If this leaf and contains exactly p (or single particle), ignore self
        if self.is_leaf() and (self.particle is p or (self.total_mass == p.mass and self.particle is p)):
            return 0.0, 0.0

        # Size of region
        s = max(self.bbox.width(), self.bbox.height())
        dx = self.center_of_mass.x() - px
        dy = self.center_of_mass.y() - py
        dist2=dx*dx+dy*dy
        distance_max2=distance_max*distance_max
        if dist2>distance_max2:#当距离太远的时候直接不计算
            return 0.0, 0.0

        #当距离超过最大距离时，不计算斥力

        #要高性能，减少除法与开方计算
        # Barnes-Hut criterion: s / dist < theta -> treat as single body
        if s*s /(theta*theta) < dist2 or self.is_leaf():
            # approximate as single particle of mass = total_mass at center_of_mass
            # repulsive force ~ repulsion * m / dist^2
            dist = math.hypot(dx, dy) + 1e-6
            force = repulsion * self.total_mass / dist2
            fx = force * (dx / dist)
            fy = force * (dy / dist)
            # note: this gives vector pointing from p to center_of_mass,
            # but repulsive should push away -> invert sign
            return -fx, -fy
        else:
            # recurse into children
            fx = fy = 0.0
            for c in self.children:
                cfx, cfy = c.compute_force_on(p, theta, repulsion)
                fx += cfx
                fy += cfy
            return fx, fy


def _dist_point_rect(px, py, rect: QRectF):
    # distance from point to rectangle center (used for fallback)
    cx = rect.x() + rect.width() / 2.0
    cy = rect.y() + rect.height() / 2.0
    return math.hypot(px - cx, py - cy)



#分布生成随机图

def generate_random_connections(mean: float) -> int:
    """生成符合泊松分布的连接数量（用指数分布近似）"""
    # JS 中的：-Math.log(1 - Math.random()) * mean
    return round(-math.log(1 - random.random()) * mean)

def generate_random_graph(node_number=200, mean=1):
    """根据 JS 逻辑生成随机图"""
    G = nx.Graph()

    # 添加节点
    for i in range(1, node_number + 1):
        G.add_node(i)

    # 随机生成边
    for i in range(1, node_number + 1):
        num_connections = generate_random_connections(mean)
        for _ in range(num_connections):
            target = random.randint(1, node_number)
            if target != i:
                G.add_edge(i, target)

    return G

# ------------------------------
# Main ForceDirectedView
# ------------------------------
class ForceDirectedView(QGraphicsView):
    def __init__(self, graph: Optional[nx.Graph] = None, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setViewportUpdateMode(QGraphicsView.MinimalViewportUpdate)

        self.scale_factor=1

        # Physics / BH params (tunable)
        self.theta = 0.6             # Barnes-Hut threshold (smaller -> more exact, larger -> faster)
        self.repulsion = 50.0      # repulsion constant (tune)
        self.spring_k = 50         # spring constant
        self.spring_length = 20    # desired edge length
        self.velocity_decay = 0.4   # damping
        self.dt = 0.04               # timestep
        self.max_disp = 30         # per-frame max displacement

        self.collision_radius=40
        self.strength=100

        self.k_centerF=3  #中心力

        self.alpha = 1.0             # simulation energy
        self.alpha_decay = 0.01      # energy decay per tick
        self.alpha_min = 0.001       # stop threshold

        # Storage
        self.node_items: Dict = {}
        self.edges: List[GraphEdge] = []

        # If user provided a networkx graph, use it; else generate demo
        self.G = graph if graph is not None else self._demo_graph(300, 0.02)

        # create items
        #所有的图信息在self.G内什么计算度也在里面
        self._create_items_from_graph(self.G)

        # timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(30)

        # iteration counter
        self.iter_count = 0

    def _demo_graph(self, n=300, p=0.05):
        G = nx.fast_gnp_random_graph(n, p)
        # add labels
        mapping = {i: f"{i}" for i in G.nodes()}
        return nx.relabel_nodes(G, mapping)

    def _create_items_from_graph(self, G: nx.Graph):
        # initial positions: random inside box
        bbox = QRectF(-500, -400, 1000, 800)

        #positions = nx.spring_layout(G, k=50, iterations=10)#预计算布局
        #scale = 300

        positions = {}
        for n in G.nodes():
            positions[n] = (random.uniform(bbox.left(), bbox.right()),
                            random.uniform(bbox.top(), bbox.bottom()))

        degrees = dict(G.degree())  # {node_id: degree}
        # create nodes
        for n, (x, y) in positions.items():
            label = str(n)
            deg = degrees.get(n, 1)
            radius = 6 + min(deg, 14)  # 可以调节映射公式
            node = GraphNode(n, x, y, radius, label=label)
            self.scene.addItem(node)
            self.node_items[n] = node

        # create edges
        for u, v in G.edges():
            n1 = self.node_items[u]; n2 = self.node_items[v]
            edge = GraphEdge(n1, n2)
            self.scene.addItem(edge)
            self.edges.append(edge)

        # fit view
        self._update_scene_rect()
        self.fitInView(self.scene.itemsBoundingRect(), Qt.KeepAspectRatio)

    def _build_quadtree(self) -> QuadTree:
        # build a bounding box slightly larger than current items bounding rect
        #self._clear_quadtree_visuals()
        #每时每刻都在重建整棵树
        rect = self.scene.itemsBoundingRect()
        margin = 50
        bbox = QRectF(rect.x() - margin, rect.y() - margin, rect.width() + 2*margin, rect.height() + 2*margin)
        root = QuadTree(bbox)
        # insert all nodes
        for node in self.node_items.values():
            root.insert(node)
        # finalize center_of_mass values
        root.finalize()
        #self._draw_quadtree_simple(root, max_depth=6)
        return root

    def _tick(self):
        # if alpha small, stop
        if self.alpha < self.alpha_min:
            # ensure final positions updated, stop timer
            self.timer.stop()
            print("计算停止")
            return
        self.iter_count += 1
        self._simulate_step()
        # decay alpha
        self.alpha *= (1.0 - self.alpha_decay)
        # update scene rect to allow panning
        #self._update_scene_rect()

    def _simulate_step(self):
        root = self._build_quadtree()
        nodes = list(self.node_items.values())

        # prepare forces dict
        forces = {n: [0.0, 0.0] for n in nodes}

        # --- repulsion via Barnes-Hut quad tree ---
        #斥力
        for n in nodes:
            fx, fy = root.compute_force_on(n, self.theta, self.repulsion)
            forces[n][0] += fx
            forces[n][1] += fy

        # --- spring (link) forces (exact per-edge) ---
        # 连接力，这个计算量不会很大，只要连接少
        for e in self.edges:
            n1 = e.node1; n2 = e.node2
            dx = n2.x() - n1.x()
            dy = n2.y() - n1.y()
            dist = math.hypot(dx, dy) + 1e-6
            # Hooke's law: F = -k * (dist - L)
            f = self.spring_k * (dist - self.spring_length)
            fx = f * (dx / dist)
            fy = f * (dy / dist)
            forces[n1][0] += fx
            forces[n1][1] += fy
            forces[n2][0] -= fx
            forces[n2][1] -= fy

        # optional center gravity to keep cluster centered
        # center = self.scene.itemsBoundingRect().center()

        #中心力，对每个节点施加
        center = QPointF(0.0, 0.0)
        
        k_center = self.k_centerF * (1.0 + (1.0 - self.alpha))  # mild center force increasing as alpha decays
        
        for n in nodes:
            dx = center.x() - n.x()
            dy = center.y() - n.y()
            forces[n][0] += dx * k_center
            forces[n][1] += dy * k_center
        
        #碰撞力，当距离过近时会产生强大的斥力
        for node in nodes:
            # 查找附近的节点
            nearby_nodes = []
            root.find_nearby_nodes(node, self.collision_radius * 2, nearby_nodes)
            
            # 对每个附近的节点应用碰撞力
            for other in nearby_nodes:
                if node is other:
                    continue
                    
                dx = other.x() - node.x()
                dy = other.y() - node.y()
                dist = math.hypot(dx, dy) + 1e-6
                
                # 如果距离小于碰撞半径
                if dist < self.collision_radius * 2:
                    # 计算重叠量
                    overlap = (self.collision_radius * 2) - dist
                    if overlap > 0:
                        # 计算排斥力（与重叠量成正比）
                        force = self.strength * overlap / dist
                        
                        fx = force * dx
                        fy = force * dy
                        
                        # 应用力（相互排斥）
                        forces[node][0] -= fx
                        forces[node][1] -= fy
                        forces[other][0] += fx
                        forces[other][1] += fy
        
        # --- integrate velocities and positions (velocity decay + limit) ---
        total_speed = 0.0
        for n in nodes:
            # if user is dragging node, skip physics update for it
            if n.isSelected():
                n.vx = 0.0; n.vy = 0.0
                continue
            fx, fy = forces[n]
            # acceleration ~ fx / m (m=1)
            ax = fx
            ay = fy
            # integrate velocity
            n.vx = (n.vx + ax * self.dt) * self.velocity_decay
            n.vy = (n.vy + ay * self.dt) * self.velocity_decay
            # cap max per-step displacement
            disp_x = n.vx * self.dt
            disp_y = n.vy * self.dt
            disp = math.hypot(disp_x, disp_y)
            if disp > self.max_disp:
                scale = self.max_disp / disp
                disp_x *= scale
                disp_y *= scale
                # scale velocities consistently
                n.vx = disp_x / self.dt
                n.vy = disp_y / self.dt
            n.setPos(n.x() + disp_x, n.y() + disp_y)
            total_speed += abs(n.vx) + abs(n.vy)

        avg_speed = total_speed / max(1, len(nodes))
        # stop condition: when avg speed small and alpha small
        if avg_speed < 0.02 and self.alpha < 0.05:
            # stop simulation
            self.alpha = 0.0
            self.timer.stop()

    def _update_scene_rect(self):
        rect = self.scene.itemsBoundingRect()
        if rect.width() < 10 or rect.height() < 10:
            rect = QRectF(-400, -300, 800, 600)
        rect = rect.adjusted(-100, -100, 100, 100)
        self.scene.setSceneRect(rect)

#辅助函数

    def _clear_quadtree_visuals(self):
        """清除之前绘制的四叉树框"""
        # 保存需要保留的items（节点和边）
        items_to_remove = []
        for item in self.scene.items():
            if isinstance(item, QGraphicsRectItem):  # 移除矩形框
                items_to_remove.append(item)
        
        # 清除场景并重新添加需要保留的items
        for item in items_to_remove:
            self.scene.removeItem(item)

    def _draw_quadtree_simple(self, node: QuadTree, max_depth=6, depth=0):
        """简化版四叉树绘制，限制深度"""
        if node is None or depth > max_depth:
            return
        #print("绘制四叉树")
        
        # 绘制当前节点框
        rect_item = QGraphicsRectItem(node.bbox)
        color = QColor(255, 100, 100, 100)  # 半透明红色
        pen = QPen(color, 2.0)
        rect_item.setPen(pen)
        rect_item.setZValue(-10)
        self.scene.addItem(rect_item)
        
        # 递归绘制子节点
        if node.children:
            for child in node.children:
                self._draw_quadtree_simple(child, max_depth, depth + 1)


    def wheelEvent(self, event):
        zoom_in = event.angleDelta().y() > 0
        factor = 1.15 if zoom_in else 1 / 1.15
        new_scale = self.scale_factor * factor
        if 0.1 < new_scale < 10:
            self.scale(factor, factor)
            self.scale_factor = new_scale
        event.accept()  # 阻止事件向上传递

    # control methods
    def restart(self):
        # reset alpha and restart timer
        self.alpha = 1.0
        self.timer.start(30)
        self.iter_count = 0
        print("计算重新开始")

    def pause(self):
        self.timer.stop()

    def resume(self):
        if self.alpha > self.alpha_min:
            self.timer.start(30)

# ------------------------------
# quick demo main
# ------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    # create a larger demo graph to test performance
    #G = nx.fast_gnp_random_graph(200, 0.01)  # tweak size/prob to test performance
    G=generate_random_graph(200,0.8)
    G = nx.relabel_nodes(G, lambda i: f"N{i}")
    w = QMainWindow()
    view = ForceDirectedView(G)
    # add simple controls
    btn_restart = QPushButton("Restart")
    btn_restart.clicked.connect(view.restart)
    btn_pause = QPushButton("Pause")
    btn_pause.clicked.connect(view.pause)
    btn_resume = QPushButton("Resume")
    btn_resume.clicked.connect(view.resume)
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.addWidget(btn_restart)
    layout.addWidget(btn_pause)
    layout.addWidget(btn_resume)
    layout.addWidget(view)
    w.setCentralWidget(container)
    w.resize(1000, 800)
    w.show()
    sys.exit(app.exec())
