# ui/components/icon_push_button.py - 仅图标的按钮，样式由 QSS + 令牌驱动
from typing import TYPE_CHECKING, Optional

from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QPushButton

from design import get_builtin_icon
from design.tokens import ThemeTokens, LIGHT_TOKENS

if TYPE_CHECKING:
    from design.theme_manager import ThemeManager


class IconPushButton(QPushButton):
    """仅图标的按钮：图标与样式由设计令牌驱动，支持主题切换时刷新。"""

    def __init__(
        self,
        icon_name: str = "settings",
        icon_size: int = 24,
        out_size: int = 32,
        hoverable: bool = True,
        theme_manager: Optional["ThemeManager"] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.setObjectName("DesignIconPushButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)
        self._icon_name = icon_name
        self._icon_size = icon_size
        self._out_size = out_size
        self._hoverable = hoverable
        self._theme_manager = theme_manager

        self.setIconSize(QSize(icon_size, icon_size))
        self.setFixedSize(out_size, out_size)
        self._refresh_icon()

        if theme_manager is not None:
            theme_manager.themeChanged.connect(self._refresh_icon)

    def _tokens(self) -> ThemeTokens:
        if self._theme_manager is not None:
            return self._theme_manager.tokens()
        return LIGHT_TOKENS

    def _refresh_icon(self) -> None:
        t = self._tokens()
        color = t.color_icon
        self.setIcon(
            get_builtin_icon(self._icon_name, size=self._icon_size, color=color)
        )

    def set_icon_name(self, icon_name: str) -> None:
        self._icon_name = icon_name
        self._refresh_icon()

    def sizeHint(self) -> QSize:
        return QSize(self._out_size, self._out_size)
