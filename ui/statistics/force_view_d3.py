# force_view_bh.py
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
#----------------------------------------------------------
import sys
import math
import random
from typing import List, Dict, Tuple, Optional,Any
import numpy as np
import networkx as nx
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsSimpleTextItem, QPushButton, QVBoxLayout, QWidget,QGraphicsRectItem,QHBoxLayout,QCheckBox,QLabel
)
from PySide6.QtGui import QBrush, QPen, QColor, QPainter
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF,Signal

import time
import functools
def timeit(func):
    """装饰器：打印函数执行耗时"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        etime=(end - start)*1000
        print(f"⏱ {func.__name__} 执行耗时: {etime:.1f} ms")
        return result
    return wrapper

# ------------------------------
# QGraphics items for node/edge
# ------------------------------
class GraphNode(QGraphicsEllipseItem):
    """Graph node with custom drag handling so that mouse drag and physics both can apply."""
    def __init__(self, node_id, x=0.0, y=0.0, radius=6, label=None):
        super().__init__(-radius, -radius, radius*2, radius*2)
        self.node_id = node_id
        self.radius = radius
        self.setPos(x, y)
        self.setBrush(QBrush(QColor("#66ccff")))
        self.setPen(QPen(Qt.black, 0.4))
        # We do custom drag; do NOT set ItemIsMovable to avoid Qt swallowing setPos
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)
        self.setFlag(QGraphicsEllipseItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsEllipseItem.ItemSendsGeometryChanges, True)
        self.setAcceptedMouseButtons(Qt.LeftButton)

        if label:
            self._label = QGraphicsSimpleTextItem(label, self)
            self._label.setPos(radius + 2, -radius - 2)
        else:
            self._label = None

        # physics state
        self.vx = 0.0
        self.vy = 0.0
        self.mass = 1.0

        # drag state
        self.dragging = False
        self._drag_offset = QPointF(0, 0)
        self.view_ref = None  # set by view when creating nodes

        self._connected_edges = []

    def add_edge(self, edge):
        self._connected_edges.append(edge)

    def set_label(self, text: str):
        if self._label:
            self._label.setText(text)
        else:
            self._label = QGraphicsSimpleTextItem(text, self)
            self._label.setPos(self.radius + 2, -self.radius - 2)

    def itemChange(self, change, value):
        if change == QGraphicsEllipseItem.ItemPositionHasChanged:
            for e in self._connected_edges:
                e.update_position()
        return super().itemChange(change, value)

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

# A simple Barnes-Hut style quadtree for many-body acceleration.
# This is a minimal implementation sufficient for ManyBodyForce.compute_force_on
class QuadTreeNode:
    def __init__(self, bbox: QRectF):
        self.bbox = bbox  # QRectF(x,y,w,h)
        self.children = [None, None, None, None]  # NW, NE, SW, SE
        self.particle: Optional[GraphNode] = None
        self.total_mass = 0.0
        self.cm_x = 0.0
        self.cm_y = 0.0

    def is_leaf(self):
        return self.children[0] is None

    def subdivide(self):
        x, y, w, h = self.bbox.x(), self.bbox.y(), self.bbox.width(), self.bbox.height()
        hw, hh = w / 2.0, h / 2.0
        self.children = [
            QuadTreeNode(QRectF(x, y, hw, hh)),             # NW
            QuadTreeNode(QRectF(x + hw, y, hw, hh)),        # NE
            QuadTreeNode(QRectF(x, y + hh, hw, hh)),        # SW
            QuadTreeNode(QRectF(x + hw, y + hh, hw, hh)),   # SE
        ]
        self.total_mass = 0.0
        self.cm_x = 0.0
        self.cm_y = 0.0

    def contains(self, x, y):
        return self.bbox.contains(QPointF(x, y))

    def insert(self, node: GraphNode):
        x, y = node.x(), node.y()
        if self.particle is None and self.is_leaf():#是叶子节点而且是空的
            self.particle = node
            self.total_mass = node.mass
            self.cm_x = x * node.mass#后面统一修正
            self.cm_y = y * node.mass
            return
        if self.is_leaf() and self.particle is not None:#是叶子节点但是满的
            # subdivide and re-insert existing particle
            existing = self.particle
            self.particle = None
            self.subdivide()
            self._put_into_child(existing)
            
        # put new particle into proper child
        self._put_into_child(node)#分裂后放到正确的位置上
        # update mass & center sums
        self.total_mass += node.mass
        self.cm_x += x * node.mass
        self.cm_y += y * node.mass

    def _put_into_child(self, node: GraphNode):
        x, y = node.x(), node.y()
        for child in self.children:
            if child.bbox.contains(QPointF(x, y)):
                child.insert(node)
                #这里要不要更新质量与质心
                #self.total_mass += node.mass
                #self.cm_x += x * node.mass
                #self.cm_y += y * node.mass
                return
        # fallback: put into first child if none contains (edge case)
        nearest = min(self.children, key=lambda c: _dist_point_rect(x, y, c.bbox))
        nearest.insert(node)
        #这个有问题，当点在边界的时候
        #self.total_mass += node.mass
        #self.cm_x += x * node.mass
        #self.cm_y += y * node.mass

    def finalize(self):
        # normalize center of mass
        if self.is_leaf():#是叶子而且有质量
            if self.total_mass > 0:
                self.cm_x /= self.total_mass
                self.cm_y /= self.total_mass
        # finalize children
        else:
            #先计算子节点的
            self.total_mass = 0.0
            self.cm_x=0.0
            self.cm_y=0.0
            for c in self.children:
                #对子叶节点计算一圈
                c.finalize()
                self.cm_x=self.cm_x+c.cm_x*c.total_mass
                self.cm_y=self.cm_y+c.cm_y*c.total_mass
                self.total_mass+=c.total_mass#质量加起来
            if self.total_mass > 0:
                self.cm_x /= self.total_mass
                self.cm_y /= self.total_mass

def _dist_point_rect(px, py, rect: QRectF):
    # distance from point to rectangle center (used for fallback)
    cx = rect.x() + rect.width() / 2.0
    cy = rect.y() + rect.height() / 2.0
    return math.hypot(px - cx, py - cy)


class Node:
    """纯计算节点，不依赖Qt"""
    __slots__ = ("id", "x", "y", "vx", "vy", "fx", "fy", "mass")

    def __init__(self, node_id, x=0.0, y=0.0):
        self.id = node_id
        self.x, self.y = x, y
        self.vx = self.vy = 0.0
        self.fx = self.fy = 0.0
        self.mass = 1.0

class Force:
    def initialize(self, nodes:list[GraphNode]): pass
    def apply(self, nodes, alpha): pass

class CenterForce(Force):
    '''O(n)'''
    def __init__(self, cx=0.0, cy=0.0, strength=0.1):
        self.cx = cx
        self.cy = cy
        self.strength = strength

    def initialize(self, nodes):
        self.nodes = nodes

    def apply(self, alpha: float):
        for n in self.nodes:
            # attract toward center
            n.vx += (self.cx - n.x()) * (self.strength * alpha)
            n.vy += (self.cy - n.y()) * (self.strength * alpha)

class LinkForce(Force):
    '''这个在连接少的时候消耗是很少的'''
    def __init__(self, links: List[Tuple[GraphNode, GraphNode]], k=0.02, distance=30.0):
        self.links = links
        self.k = k
        self.distance = distance

    def initialize(self, nodes):
        # nodes not needed here, links already hold node refs
        self.nodes = nodes
    
    
    def apply(self, alpha: float):
        for a, b in self.links:
            dx = b.x() - a.x()
            dy = b.y() - a.y()
            dist = math.hypot(dx, dy) + 1e-6
            # FR-style attractive force: proportional to (dist - desired)
            # include alpha to slowly reduce movement over time if desired
            f = self.k * (dist - self.distance) * alpha
            fx = f * dx / dist
            fy = f * dy / dist
            a.vx += fx
            a.vy += fy
            b.vx -= fx
            b.vy -= fy

class ManyBodyForce(Force):
    """Repulsive force. Modes:
       - mode='brute' : O(N^2) pairwise repulsion
       - mode='barnes' : Barnes-Hut approximate via QuadTree
       这个是最消耗时间的，需要大量的优化
    """
    def __init__(self, strength=100.0, theta=0.6):
        self.strength = strength
        self.theta = theta
        self.theta2=theta*theta
        self.root=None#这个是给点建立的树
        

    def initialize(self, nodes):
        self.nodes = nodes
    

    def _build_quadtree(self):
        '''建四叉树'''
        #计算点集的最大外框
        rect = compute_bounding_box_numpy(self.nodes)
        margin = 20
        bbox = QRectF(rect.x() - margin, rect.y() - margin, rect.width() + 2*margin, rect.height() + 2*margin)
        root = QuadTreeNode(bbox)#这里建树
        for n in self.nodes:
            root.insert(n)
        root.finalize()
        return root

    
    def _compute_force_barnes_on(self, root: QuadTreeNode, target: GraphNode)-> Tuple[float, float]:
        # recursively compute approximate repulsion on target
        distance_max2=90000#最大计算斥力距离，当距离超过这个时不计算距离

        def recurse(node: QuadTreeNode):
            if node.total_mass == 0:#当节点为空时
                return 0.0, 0.0
            
            # If this leaf and contains exactly p (or single particle), ignore self,自己与自己没有斥力
            if node.is_leaf() and (node.particle is target or (node.total_mass == target.mass and node.particle is target)):
                return 0.0, 0.0
            
            dx = node.cm_x - target.x()
            dy = node.cm_y - target.y()
            dist2=dx*dx+dy*dy+1e-6#防止除以0的错误
            
            s = max(node.bbox.width(), node.bbox.height())
            
            if dist2>distance_max2:#当距离太远的时候直接不计算
                return 0.0, 0.0

            # Barnes-Hut criterion
            if node.is_leaf() or s*s /self.theta2 < dist2 :
                # treat node as single body
                dist = math.hypot(dx, dy) + 1e-6
                force = self.strength * node.total_mass / dist2
                return -force * (dx / dist), -force * (dy / dist)
            else:#迭代计算每块的力加起来
                fx = fy = 0.0
                for c in node.children:
                    if c and c.total_mass > 0:
                        cfx, cfy = recurse(c)
                        fx += cfx; fy += cfy
                return fx, fy
        return recurse(root)

    @timeit
    def apply(self, alpha: float):
        self.root = self._build_quadtree()
        start=time.perf_counter()
        for n in self.nodes:
            fx, fy = self._compute_force_barnes_on(self.root, n)
            n.vx += fx * alpha
            n.vy += fy * alpha
        print((time.perf_counter() - start) * 1000.0)  # 转成ms

class CollisionForce(Force):
    """Collision (prevent overlap) using quadtree visit and local corrections (D3-style)."""
    def __init__(self, radius=lambda n: getattr(n, "radius", 20), strength=1.0, iterations=1):

        self.strength = strength
        self.iterations = iterations
        # 如果 radius 是数值，就自动包装成函数；否则假设是函数
        if callable(radius):#如果是函数传入，就用函数
            self.radius_getter = radius
        else:#是固定数据
            const_radius = float(radius)
            self.radius_getter = lambda n: const_radius

    def initialize(self, nodes):
        self.nodes = nodes
        self.radii = [self.radius_getter(n) for n in nodes]

    
    def apply(self, alpha: float):
        # For simplicity we will use a quadtree-like broad phase simulated by grid-binning
        # A more exact translation of D3's quadtree approach could be done (but more code).
        # Here we use cell hashing to find nearby candidates efficiently.
        nodes = self.nodes
        n = len(nodes)
        if n == 0:
            return

        # build spatial hash
        # cell size = max radius * 2
        max_r = max(self.radii) if self.radii else 1.0
        cell = max(1.0, max_r * 2)
        grid = {}
        def cell_key(x, y):
            return (int(x // cell), int(y // cell))

        for it in range(self.iterations):
            grid.clear()
            for i, node in enumerate(nodes):
                k = cell_key(node.x(), node.y())
                grid.setdefault(k, []).append(i)

            for i, node in enumerate(nodes):
                ri = self.radii[i]
                kx, ky = cell_key(node.x(), node.y())
                # check neighbouring cells
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        bucket = grid.get((kx+dx, ky+dy))
                        if not bucket:
                            continue
                        for j in bucket:
                            if j <= i:
                                continue
                            other = nodes[j]
                            rj = self.radii[j]
                            dxn = node.x() - other.x(); dyn = node.y() - other.y()
                            dist2 = dxn*dxn + dyn*dyn
                            minr = ri + rj
                            if dist2 < (minr * minr):
                                dist = math.sqrt(dist2) if dist2 > 1e-6 else 1e-3
                                # overlap amount
                                overlap = (minr - dist) / dist * 0.5 * self.strength * alpha
                                # move proportional to mass (equal mass here)
                                nx_move = dxn * overlap
                                ny_move = dyn * overlap
                                node.vx += nx_move
                                node.vy += ny_move
                                other.vx -= nx_move
                                other.vy -= ny_move

def compute_bounding_box_numpy(points: List[GraphNode]) -> QRectF:
    """使用NumPy加速计算外接矩形"""
    if not points:
        return QRectF(0, 0, 0, 0)
    
    # 转换为NumPy数组
    points_array = np.array([[p.x(), p.y()] for p in points])
    
    min_coords = np.min(points_array, axis=0)
    max_coords = np.max(points_array, axis=0)
    
    return QRectF(
        min_coords[0], min_coords[1],
        max_coords[0] - min_coords[0],
        max_coords[1] - min_coords[1]
    )
# ------------------------------
# Simulation controller
# ------------------------------
class Simulation:
    def __init__(self, nodes: List[GraphNode]):
        self.nodes = nodes
        self.forces: Dict[str, Force] = {}
        # physics params
        self.alpha = 1.0
        self.alpha_decay = 0.02
        self.alpha_min = 0.001

        self.velocity_decay = 0.9  # similar to d3.velocityDecay
        self.dt = 0.5      #模拟时间间隔
        self.max_disp = 30.0#每次模拟最大位移距离

        # internal
        self._active = False

    def add_force(self, name: str, force: Force):
        self.forces[name] = force
        force.initialize(self.nodes)

    def remove_force(self, name: str):
        if name in self.forces:
            del self.forces[name]

    
    def tick(self):
        '''单步模拟核心函数'''
        if self.alpha <= self.alpha_min:
            self._active = False
            return
        # apply each force in turn (each modifies node.vx/vy)
        for f in list(self.forces.values()):
            f.apply(self.alpha)
        # integrate velocities -> positions
        total_speed = 0.0
        for n in self.nodes:
            # If node being dragged, we still update its velocity but we won't override mouse pos
            if getattr(n, "dragging", False):
                # apply velocity decay but don't apply large physics displacement
                n.vx *= self.velocity_decay
                n.vy *= self.velocity_decay
                # optionally tug the node a little toward physics (small fraction)
                tug = 0.05
                n.setPos(n.x() + n.vx * self.dt * tug, n.y() + n.vy * self.dt * tug)
                total_speed += abs(n.vx) + abs(n.vy)
                continue

            # normal integrate
            n.vx *= self.velocity_decay
            n.vy *= self.velocity_decay
            dx = n.vx * self.dt
            dy = n.vy * self.dt
            disp = math.hypot(dx, dy)
            if disp > self.max_disp:#位移距离过大时的限制
                scale = self.max_disp / disp
                dx *= scale; dy *= scale
                n.vx = dx / self.dt; n.vy = dy / self.dt
            n.setPos(n.x() + dx, n.y() + dy)
            total_speed += abs(n.vx) + abs(n.vy)

        # cool down
        self.alpha *= (1.0 - self.alpha_decay)
        avg_speed = total_speed / max(1, len(self.nodes))
        if avg_speed < 0.01 and self.alpha < 0.05:
            self._active = False

    def start(self):
        self._active = True

    def stop(self):
        self._active = False

    def pause(self):
        self._active = False

    def resume(self):
        if self.alpha > self.alpha_min:
            self._active = True

    def restart(self):
        self.alpha = 1.0
        self._active = True

    def active(self):
        return self._active


def create_G():
    N = 100
    G = nx.Graph()

    # 添加节点
    for i in range(N):
        G.add_node(i)

    # 手动创建度分布
    # 5 个 hub 节点，连接 20 个节点
    hub_nodes = [0, 1, 2, 3, 4]
    for hub in hub_nodes:
        for target in range(5, 25):  # 每个 hub 连接 20 个低度节点
            G.add_edge(hub, target)

    # 中等节点度节点，度大约 5~10
    for i in range(25, 50):
        for j in range(i+1, i+6):
            if j < N:
                G.add_edge(i, j)

    # 剩下低度节点，随机少量连接
    for i in range(50, N):
        if i+1 < N:
            G.add_edge(i, i+1)
        if i+3 < N:
            G.add_edge(i, i+3)
    return G
# ------------------------------
# A QGraphicsView that uses Simulation
# ------------------------------
class ForceView(QGraphicsView):

    c_time=Signal(float)
    def __init__(self, G: Optional[nx.Graph] = None, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

        self.node_items: Dict[Any, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.scale_factor=1
        self.axis_items=[]
        self.show_quadtree=False#默认不显示
        

        # build graph
        self.G = G if G is not None else nx.fast_gnp_random_graph(500, 0.005)
        # get positions via networkx spring layout (precompute)
        positions = nx.spring_layout(self.G, k=0.1, iterations=50, seed=42)
        scale = 400.0
        degrees = dict(self.G.degree())

        # create nodes & edges
        for n, (x, y) in positions.items():
            # radius scaled by degree
            deg = degrees.get(n, 1)
            radius = 4 + min(20, deg)  # clamp
            label = str(n)
            node = GraphNode(n, x*scale, y*scale, radius=radius, label=label)
            node.view_ref = self
            self.scene.addItem(node)
            self.node_items[n] = node

        for u, v in self.G.edges():
            n1 = self.node_items[u]; n2 = self.node_items[v]
            edge = GraphEdge(n1, n2)
            self.scene.addItem(edge)
            self.edges.append((n1, n2))
            # edge item for visuals
            # keep a QGraphicsLineItem too if desired: GraphEdge handles it via update_position()

        # create simulation with nodes
        nodes = list(self.node_items.values())
        self.simulation = Simulation(nodes)
        # add forces
        self.many = ManyBodyForce(strength=1000.0, theta=0.6)
        self.simulation.add_force("manybody", self.many)
        link = LinkForce(self.edges, k=0.02, distance=40.0)
        self.simulation.add_force("link", link)
        center = CenterForce(0.0, 0.0, strength=0.002)
        self.simulation.add_force("center", center)
        #collide = CollisionForce(radius=40.0, strength=2.0, iterations=1)
        #self.simulation.add_force("collide", collide)

        # timer-driven ticks
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._on_timer)
        self.timer.start(16)

        # 动态帧控制参数
        self._target_frame_time = 16  # 目标帧间隔(ms) ≈ 60 FPS
        self._min_interval = 10
        self._max_interval = 100

        self.simulation.start()
        # set initial scene rect once
        self._update_scene_rect(init=True)
        

    def _on_timer(self):
        import time
        start = time.perf_counter()
        
        self._clear_quadtree_visuals()

        # === 执行一次物理模拟 ===
        if self.simulation.active():
            self.simulation.tick()

        elapsed = (time.perf_counter() - start) * 1000.0  # 转成ms
        self.c_time.emit(elapsed)
        

        #更新要显示的内容
        if self.show_quadtree:
            self._draw_quadtree_simple(self.many.root)


    def _update_scene_rect(self, init=False):
        rect = self.scene.itemsBoundingRect()
        if init:
            if rect.width() < 10 or rect.height() < 10:
                rect = QRectF(-400, -300, 800, 600)
            rect = rect.adjusted(-200, -200, 200, 200)
            self.scene.setSceneRect(rect)
        else:
            # do not constantly reset rect to avoid view jumping; optionally expand if node leaves
            current = self.scene.sceneRect()
            need_expand = False
            for n in self.node_items.values():
                p = n.pos()
                if not current.contains(p):
                    need_expand = True
                    break
            if need_expand:
                new_rect = current.adjusted(-400, -400, 400, 400)
                self.scene.setSceneRect(new_rect)

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

    def _draw_quadtree_simple(self, node: QuadTreeNode, max_depth=6, depth=0):
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
        '''这个可以缩放'''
        zoom_in = event.angleDelta().y() > 0
        factor = 1.15 if zoom_in else 1 / 1.15
        new_scale = self.scale_factor * factor
        if 0.1 < new_scale < 10:
            self.scale(factor, factor)
            self.scale_factor = new_scale
        event.accept()  # 阻止事件向上传递


    def set_show_quadtree(self,state):
        
        if state == Qt.CheckState.Checked:
            self.show_quadtree = True
        else:
            self.show_quadtree = False
            print(f"改变状态为{state}")

    def show_coordinate_sys(self,state):
        '''显示坐标轴'''
        
        if state == Qt.CheckState.Checked:
            print("添加坐标轴")
            pen = QPen(QColor(0, 0, 255))  # 蓝色
            pen.setWidth(2)
            x_axis = QGraphicsLineItem(0, 0, 500, 0)
            x_axis.setPen(pen)
            self.scene.addItem(x_axis)
            pen = QPen(QColor(255, 0, 0))  # 红色
            pen.setWidth(2)
            y_axis = QGraphicsLineItem(0, 0, 0, 500)
            y_axis.setPen(pen)
            self.scene.addItem(y_axis)
            self.axis_items.append(x_axis)
            self.axis_items.append(y_axis)
        else:
            print("删除坐标轴")
            for item in self.axis_items:
                self.scene.removeItem(item)
            self.axis_items=[]

# ------------------------------
# Demo main
# ------------------------------
def main():
    app = QApplication(sys.argv)
    w = QMainWindow()
    view = ForceView()
    # controls
    btn_restart = QPushButton("Restart")
    btn_restart.clicked.connect(view.simulation.restart)
    btn_pause = QPushButton("Pause")
    btn_pause.clicked.connect(view.simulation.pause)
    btn_resume = QPushButton("Resume")
    btn_resume.clicked.connect(view.simulation.resume)
    show_quadtree=QCheckBox("显示四叉树")
    show_quadtree.setChecked(False)
    show_quadtree.checkStateChanged.connect(view.set_show_quadtree)

    show_coordinate_sys=QCheckBox("显示坐标轴")
    show_coordinate_sys.setChecked(False)
    show_coordinate_sys.checkStateChanged.connect(view.show_coordinate_sys)

    label1=QLabel()

    container = QWidget()
    mainlayout = QHBoxLayout(container)
    mainlayout.addWidget(view)
    vlayout=QVBoxLayout()
    vlayout.addWidget(label1)
    vlayout.addWidget(btn_restart)
    vlayout.addWidget(btn_pause)
    vlayout.addWidget(btn_resume)
    vlayout.addWidget(show_quadtree)
    vlayout.addWidget(show_coordinate_sys)
    mainlayout.addLayout(vlayout)
    view.c_time.connect(lambda c:label1.setText(f"单步模拟消耗{c:.1f}毫秒"))

    w.setCentralWidget(container)
    w.resize(1000, 700)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()