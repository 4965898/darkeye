from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPen, QBrush, QColor, QPainterPathStroker, QImage, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QWidget, QVBoxLayout, QAbstractButton

from config import ICONS_PATH


class OctagonButton(QAbstractButton):
    """
    八边形菜单按钮
    - 只保留图标（可选）+ 内部绘制
    - hover 时高亮
    - 支持选中状态
    - 使用 tooltip 显示文本提示
    """

    def __init__(self, menu_id: str, text: str, icon_name: str | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.menu_id = menu_id
        self._text = text
        self._icon_path: str | None = None
        if icon_name:
            self._icon_path = str(ICONS_PATH / icon_name)

        # 显示提示文本
        self.setToolTip(text)

        # 统一按钮尺寸（接近正方形）
        self.setFixedSize(40, 40)

        # 状态
        self._is_selected = False
        self._is_hovered = False

        # 开启鼠标跟踪以便 hover 效果
        self.setMouseTracking(True)

    # --------- 状态 API ---------
    def set_selected(self, selected: bool) -> None:
        if self._is_selected != selected:
            self._is_selected = selected
            self.update()

    def is_selected(self) -> bool:
        return self._is_selected

    # --------- 事件处理 ---------
    def enterEvent(self, event) -> None:  # type: ignore[override]
        self._is_hovered = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # type: ignore[override]
        self._is_hovered = False
        self.update()
        super().leaveEvent(event)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    # --------- 绘制八边形 ---------
    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        rect = self.rect()
        w = rect.width()
        h = rect.height()
        x = rect.x()
        y = rect.y()

        # 通过“切角”生成近似规则八边形
        dx = w * 0.22
        dy = h * 0.22

        path = QPainterPath()
        path.moveTo(x + dx, y)
        path.lineTo(x + w - dx, y)
        path.lineTo(x + w, y + dy)
        path.lineTo(x + w, y + h - dy)
        path.lineTo(x + w - dx, y + h)
        path.lineTo(x + dx, y + h)
        path.lineTo(x, y + h - dy)
        path.lineTo(x, y + dy)
        path.closeSubpath()

        # 颜色根据状态变化
        if self._is_selected:
            fill_color = QColor("#F5FFA0")  # 选中高亮
            border_color = QColor("#FFFFFF")
        elif self._is_hovered:
            fill_color = QColor("#F5FFA0")  # hover 高亮
            border_color = QColor("#FFFFFF")
        else:
            fill_color = QColor("#FFFFFF")  # 普通
            border_color = QColor("#FFFFFF")


        painter.setRenderHint(QPainter.Antialiasing)

        painter.setPen(Qt.NoPen) 
        painter.setBrush(QBrush(fill_color))
        painter.drawPath(path)

        # 在八边形内部绘制图标（若有），直接从 SVG 渲染到 QImage 再转为 QPixmap
        if self._icon_path is not None:
            icon_size = int(min(w, h) * 0.55)

            image = QImage(icon_size, icon_size, QImage.Format_ARGB32_Premultiplied)
            image.fill(Qt.GlobalColor.transparent)

            renderer = QSvgRenderer(self._icon_path)
            svg_painter = QPainter(image)
            renderer.render(svg_painter)
            svg_painter.end()

            pix = QPixmap.fromImage(image)
            ix = x + (w - icon_size) / 2
            iy = y + (h - icon_size) / 2
            painter.drawPixmap(int(ix), int(iy), pix)


class Sidebar2(QWidget):
    """
    简化版侧边栏：
    - 只保留一列八边形按钮
    - 所有按钮在侧边栏中垂直居中
    - hover 显示 tooltip，点击发射 menu_id
    - 尽量兼容现有 Sidebar 的接口（itemClicked / selectedChanged / select 等）
    """

    itemClicked = Signal(str)
    selectedChanged = Signal(str)

    def __init__(self, menu_defs=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # 与旧 Sidebar 接口保持一致
        if menu_defs is None:
            self.menu_defs = []
        else:
            self.menu_defs = menu_defs

        self._buttons: dict[str, OctagonButton] = {}
        self._current_id: str | None = None

        # 背景：用 paintEvent 绘制八边形（直倒角），不用圆角
        self.setFixedWidth(72)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet("Sidebar2 { background-color: transparent; }")
        self.setAutoFillBackground(False)

        # 布局：按钮整体垂直居中
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        layout.addStretch(1)
        for mid, text, icon_name in self.menu_defs:
            btn = OctagonButton(mid, text, icon_name, self)
            btn.clicked.connect(lambda _=False, m=mid: self._on_button_clicked(m))
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
            self._buttons[mid] = btn
        layout.addStretch(1)

        # 默认选中第一个
        if self.menu_defs:
            first_id = self.menu_defs[0][0]
            if first_id in self._buttons:
                self._current_id = first_id
                self._buttons[first_id].set_selected(True)

    def paintEvent(self, event) -> None:  # type: ignore[override]
        """绘制侧边栏整体背景为八边形（直倒角），上下留白 20px，左右各 5px。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        # 上下空白 20px，左右各 5px
        r = self.rect().adjusted(5, 20, -5, -20)
        w, h = r.width(), r.height()
        x, y = r.x(), r.y()
        chamfer = 12

        path = QPainterPath()
        path.moveTo(x + chamfer, y)
        path.lineTo(x + w - chamfer, y)
        path.lineTo(x + w, y + chamfer)
        path.lineTo(x + w, y + h - chamfer)
        path.lineTo(x + w - chamfer, y + h)
        path.lineTo(x + chamfer, y + h)
        path.lineTo(x, y + h - chamfer)
        path.lineTo(x, y + chamfer)
        path.closeSubpath()

        painter.setPen(QPen(QColor("#D4ECD7"), 1))
        painter.setBrush(QBrush(QColor("#D4ECD7")))
        painter.drawPath(path)

    # --------- 兼容接口 ---------
    def _on_button_clicked(self, menu_id: str) -> None:
        # 与旧 Sidebar 一样：点击当前按钮再次会取消选中，并发射空 selectedChanged
        if self._current_id == menu_id:
            btn = self._buttons.get(menu_id)
            if btn:
                btn.set_selected(False)
            self._current_id = None
            self.selectedChanged.emit("")
        else:
            prev_btn = self._buttons.get(self._current_id or "")
            if prev_btn:
                prev_btn.set_selected(False)

            new_btn = self._buttons.get(menu_id)
            if new_btn:
                new_btn.set_selected(True)
            self._current_id = menu_id
            self.selectedChanged.emit(menu_id)

        self.itemClicked.emit(menu_id)

    def get_selected_id(self):
        return self._current_id

    def clear_selection(self) -> None:
        if self._current_id is None:
            return
        btn = self._buttons.get(self._current_id)
        if btn:
            btn.set_selected(False)
        self._current_id = None
        self.selectedChanged.emit("")

    def select(self, menu_id: str) -> None:
        if self._current_id == menu_id:
            return

        prev_btn = self._buttons.get(self._current_id or "")
        if prev_btn:
            prev_btn.set_selected(False)

        new_btn = self._buttons.get(menu_id)
        if new_btn:
            new_btn.set_selected(True)
            self._current_id = menu_id
            self.selectedChanged.emit(menu_id)

    def toggle_menu(self) -> None:
        """
        为兼容旧 Sidebar 接口而保留的空方法。
        Sidebar2 不再提供展开/折叠动画。
        """
        pass

