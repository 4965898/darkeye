import sys
from pathlib import Path
root_dir = Path(__file__).resolve().parents[2]  # 上两级
sys.path.insert(0, str(root_dir))

from PySide6.QtWidgets import  QLabel, QColorDialog,QApplication,QWidget,QVBoxLayout,QGraphicsDropShadowEffect
from PySide6.QtGui import QColor
from PySide6.QtCore import Qt,Signal, QPoint, QEvent
from ui.basic.Effect import ShadowEffectMixin
import logging

from ui.basic.ColorPickerOKLCH import ColorWheelSimple

class ColorPicker(QLabel):
    colorChanged = Signal(str)

    def __init__(self, color: QColor = QColor("white"), parent=None):
        super().__init__(parent)
        self._color = color
        self.setAlignment(Qt.AlignCenter)
        self._update_color(self._color)
        self.setMaximumHeight(40)

        # 自定义点击事件
        self.mousePressEvent = self.show_color_wheel

        # 悬浮颜色选择器（延迟创建）
        self._color_wheel = None

        # 初始阴影（可选）
        self.set_shadow()

    def set_shadow(self):
        """添加阴影效果（可选）"""
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(5)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.setGraphicsEffect(shadow)

    def get_color(self) -> str:
        return self._color.name()

    def set_color(self, color: str):
        self._update_color(QColor(color))

    def _update_color(self, new_color: QColor):
        self._color = new_color
        self.setText(self._color.name())

        # 自动计算文字颜色（黑/白对比）
        text_color = "#000000" if new_color.lightness() > 128 else "#FFFFFF"

        self.setStyleSheet(
            f"background-color: {self._color.name()};"
            f"border-radius: 12px;"
            f"color: {text_color};"
            f"font-size: 24px;"
        )

        self.colorChanged.emit(new_color.name())

    def show_color_wheel(self, event):
        """点击标签时弹出悬浮颜色选择器"""
        print("点击事件")
        if self._color_wheel is None:
            self._color_wheel = ColorWheelSimple()

            # 设置为无边框 + 置顶 + 透明背景（可选）
            self._color_wheel.setWindowFlags(
                Qt.WindowType.FramelessWindowHint |
                Qt.WindowType.WindowStaysOnTopHint |
                Qt.WindowType.Popup
            )
            #self._color_wheel.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

            # 添加阴影（可选，更美观）
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(20)
            shadow.setColor(QColor(0, 0, 0, 180))
            shadow.setOffset(0, 8)
            self._color_wheel.setGraphicsEffect(shadow)

        self._color_wheel.adjustSize()           # ← 强制计算 sizeHint 并调整
        self._color_wheel.show()                 # 先 show 一次（隐藏状态下也有效）
        self._color_wheel.hide()               # 如果不想闪烁，可注释掉 show/hide

        # 位置：标签正上方，水平居中
        global_pos = self.mapToGlobal(QPoint(0, 0))
        wheel_width = self._color_wheel.width()
        label_width = self.width()
        x = global_pos.x() + (label_width - wheel_width) // 2
        y = global_pos.y() - self._color_wheel.height() - 10  # 上方 10px 间距
        print(f"{x},{y}")

        self._color_wheel.move(x, y)

        # 显示并激活
        self._color_wheel.show()
        self._color_wheel.activateWindow()
        self._color_wheel.setFocus()

        self._color_wheel.wheel.vm.L_changed.connect(lambda:self._update_color(QColor(self._color_wheel.wheel.get_OKLCH_hexrgb())))
        self._color_wheel.wheel.vm.C_changed.connect(lambda:self._update_color(QColor(self._color_wheel.wheel.get_OKLCH_hexrgb())))
        self._color_wheel.wheel.vm.H_changed.connect(lambda:self._update_color(QColor(self._color_wheel.wheel.get_OKLCH_hexrgb())))

        # 监听点击位置 → 关闭
        self._color_wheel.installEventFilter(self)

        # 初始设置当前颜色（如果 ColorWheelSimple 支持）
        self._color_wheel.setInitialColor(self._color.name())  # 如果有这个方法

    def eventFilter(self, obj, event):
        """监听悬浮窗的鼠标点击事件，判断是否点击在窗口外"""
        if obj == self._color_wheel:
            # 只处理鼠标按下事件
            if event.type() == QEvent.Type.MouseButtonPress:
                # 获取点击的全局坐标（推荐用 globalPosition）
                global_pos = event.globalPosition().toPoint()
                
                # 判断点击位置是否在窗口矩形内
                if self._color_wheel.rect().contains(self._color_wheel.mapFromGlobal(global_pos)):
                    # 点击在窗口内部 → 不关闭，继续传递给子控件
                    print("点击在窗口内，继续处理")
                    return False
                else:
                    # 点击在窗口外部 → 关闭窗口
                    print("点击在窗口外部，关闭")
                    self._color_wheel.hide()
                    self._color_wheel.removeEventFilter(self)
                    
                    # 获取最终颜色并更新
                    hex_color = self._color_wheel.getHexColor()
                    if hex_color:
                        self._update_color(QColor(hex_color))
                    
                    return True  # 事件已处理，不继续传播

        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        """点击标签外部时，如果悬浮窗已打开，也关闭它"""
        if self._color_wheel and self._color_wheel.isVisible():
            # 判断点击是否在悬浮窗外
            global_pos = self.mapToGlobal(event.pos())
            if not self._color_wheel.geometry().contains(global_pos):
                self._color_wheel.hide()
                self._color_wheel.removeEventFilter(self)

        super().mousePressEvent(event)


# 测试使用
if __name__ == "__main__":
    app = QApplication([])
    widget = QWidget()
    layout = QVBoxLayout(widget)

    picker = ColorPicker(QColor("#FF4081"))
    picker.colorChanged.connect(lambda c: print("颜色已更改:", c))
    layout.addWidget(picker)

    widget.resize(400, 300)
    widget.show()
    app.exec()