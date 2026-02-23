# design/demo.py - 展示设计系统组件与主题切换（从项目根目录运行：python -m design.demo）
import sys
from pathlib import Path

# 保证从项目根解析 config、ui
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtCore import Qt

from design import ThemeManager, ThemeId
from ui.components import Button, Label, Input


def main():
    app = QApplication(sys.argv)
    theme_mgr = ThemeManager()
    theme_mgr.set_theme(app, ThemeId.LIGHT)

    win = QWidget()
    win.setWindowTitle("设计系统组件 Demo")
    win.setMinimumWidth(360)
    layout = QVBoxLayout(win)
    layout.setSpacing(12)

    layout.addWidget(Label("设计系统组件 Demo"))
    layout.addWidget(Input())
    layout.addWidget(Input())
    input_placeholder = Input()
    input_placeholder.setPlaceholderText("占位符示例")
    layout.addWidget(input_placeholder)

    btn_row = QHBoxLayout()
    btn_row.addWidget(Button("默认按钮"))
    btn_row.addWidget(Button("主要按钮", variant="primary"))
    layout.addLayout(btn_row)

    def toggle_theme():
        app = QApplication.instance()
        if theme_mgr.current() == ThemeId.LIGHT:
            theme_mgr.set_theme(app, ThemeId.DARK)
            switch_btn.setText("切换为浅色")
        else:
            theme_mgr.set_theme(app, ThemeId.LIGHT)
            switch_btn.setText("切换为深色")

    switch_btn = Button("切换为深色", variant="primary")
    switch_btn.clicked.connect(toggle_theme)
    layout.addWidget(switch_btn)

    layout.addStretch()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
