# design/demo.py - 展示设计系统组件与主题切换（从项目根目录运行：python -m design.demo）
import sys
from pathlib import Path

# 保证从项目根解析 config、ui
_root = Path(__file__).resolve().parent.parent
if str(_root) not in sys.path:
    sys.path.insert(0, str(_root))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QFrame
from PySide6.QtCore import Qt

from design import ThemeManager, ThemeId, get_builtin_icon
from ui.components import Button, Label, Input

BUILTIN_ICON_NAMES = (
    "close",
    "check",
    "arrow_up",
    "arrow_down",
    "arrow_left",
    "arrow_right",
    "plus",
    "minus",
)


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

    layout.addWidget(Label("内置图标"))
    icon_row = QHBoxLayout()
    for name in BUILTIN_ICON_NAMES:
        btn = Button(icon=get_builtin_icon(name, size=20), icon_size=20)
        btn.setToolTip(name)
        btn.setMinimumWidth(40)
        icon_row.addWidget(btn)
    layout.addLayout(icon_row)

    def update_theme_buttons():
        for tid, btn in theme_buttons.items():
            btn.setProperty("variant", "primary" if theme_mgr.current() == tid else "default")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def make_theme_switch(theme_id: ThemeId, label: str):
        def on_click():
            app = QApplication.instance()
            theme_mgr.set_theme(app, theme_id)
            update_theme_buttons()

        btn = Button(label, variant="primary" if theme_mgr.current() == theme_id else "default")
        btn.clicked.connect(on_click)
        return btn

    layout.addWidget(Label("主题切换"))
    theme_buttons = {
        ThemeId.LIGHT: make_theme_switch(ThemeId.LIGHT, "浅色"),
        ThemeId.DARK: make_theme_switch(ThemeId.DARK, "深色"),
        ThemeId.RED: make_theme_switch(ThemeId.RED, "红色"),
    }
    theme_row = QHBoxLayout()
    for btn in theme_buttons.values():
        theme_row.addWidget(btn)
    layout.addLayout(theme_row)

    layout.addStretch()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
