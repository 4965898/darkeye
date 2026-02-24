# design/icon.py - 将路径或内联 SVG 字符串转为 QIcon
from pathlib import Path
from typing import Union

from PySide6.QtCore import QByteArray
from PySide6.QtGui import QIcon, QImage, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer


def _device_pixel_ratio() -> float:
    """获取主屏设备像素比，高 DPI 下用于渲染更清晰的图标。"""
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app and app.primaryScreen() is not None:
            return app.primaryScreen().devicePixelRatio()
    except Exception:
        pass
    return 1.0

# ---------- 内联常用图标（24x24 viewBox，stroke=currentColor 便于着色） ----------
_SVG_VIEW = 'xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"'

SVG_CLOSE = f'<svg {_SVG_VIEW}><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>'
SVG_CHECK = f'<svg {_SVG_VIEW}><path d="M20 6 9 17l-5-5"/></svg>'
SVG_ARROW_UP = f'<svg {_SVG_VIEW}><path d="m18 15-6-6-6 6"/></svg>'
SVG_ARROW_DOWN = f'<svg {_SVG_VIEW}><path d="m6 9 6 6 6-6"/></svg>'
SVG_ARROW_LEFT = f'<svg {_SVG_VIEW}><path d="m15 18-6-6 6-6"/></svg>'
SVG_ARROW_RIGHT = f'<svg {_SVG_VIEW}><path d="m9 18 6-6-6-6"/></svg>'
SVG_PLUS = f'<svg {_SVG_VIEW}><path d="M12 5v14"/><path d="M5 12h14"/></svg>'
SVG_MINUS = f'<svg {_SVG_VIEW}><path d="M5 12h14"/></svg>'

BUILTIN_ICONS = {
    "close": SVG_CLOSE,
    "check": SVG_CHECK,
    "arrow_up": SVG_ARROW_UP,
    "arrow_down": SVG_ARROW_DOWN,
    "arrow_left": SVG_ARROW_LEFT,
    "arrow_right": SVG_ARROW_RIGHT,
    "plus": SVG_PLUS,
    "minus": SVG_MINUS,
}


def _normalize_size(size: Union[int, tuple]) -> tuple:
    if isinstance(size, int):
        return (size, size)
    return (size[0], size[1])


def _load_svg_string(svg_source: Union[str, Path]) -> str:
    """返回用于渲染的 SVG 字符串。svg_source 为内联 XML 或文件路径。"""
    s = svg_source
    if isinstance(s, Path):
        return s.read_text(encoding="utf-8")
    s = s.strip()
    if s.startswith("<") or "<?xml" in s[:100]:
        return s
    path = Path(s)
    if path.exists():
        return path.read_text(encoding="utf-8")
    return s


def _apply_color(svg_data: str, color: str) -> str:
    """将 SVG 中的 currentColor 替换为指定颜色。"""
    if 'fill="none"' in svg_data or "fill='none'" in svg_data:
        svg_data = svg_data.replace('stroke="currentColor"', f'stroke="{color}"')
        svg_data = svg_data.replace("stroke='currentColor'", f"stroke='{color}'")
    if "currentColor" in svg_data:
        svg_data = svg_data.replace('fill="currentColor"', f'fill="{color}"')
        svg_data = svg_data.replace("fill='currentColor'", f"fill='{color}'")
        svg_data = svg_data.replace('stroke="currentColor"', f'stroke="{color}"')
        svg_data = svg_data.replace("stroke='currentColor'", f"stroke='{color}'")
    return svg_data


def svg_to_icon(
    svg_source: Union[str, Path, QIcon],
    size: Union[int, tuple] = 16,
    color: Union[str, None] = None,
) -> QIcon:
    """从文件路径、内联 SVG 字符串或已有 QIcon 得到 QIcon。

    - svg_source 为 str 且形如 XML（以 < 开头或含 <?xml）时视为内联 SVG 字符串。
    - 为 str/Path 且为路径时读取文件内容再渲染。
    - 为 QIcon 时直接返回。
    - size: 渲染尺寸，int 为宽高同，或 (w, h)。
    - color: 可选，替换 SVG 中 currentColor 后渲染。
    """
    if isinstance(svg_source, QIcon):
        return svg_source

    w, h = _normalize_size(size)
    svg_data = _load_svg_string(svg_source)
    if color:
        svg_data = _apply_color(svg_data, color)

    renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))
    if not renderer.isValid():
        return QIcon()

    ratio = _device_pixel_ratio()
    rw, rh = int(w * ratio), int(h * ratio)
    rw, rh = max(1, rw), max(1, rh)
    image = QImage(rw, rh, QImage.Format.Format_ARGB32)
    image.fill(0)
    painter = QPainter(image)
    renderer.render(painter)
    painter.end()
    pixmap = QPixmap.fromImage(image)
    if ratio > 1.0:
        pixmap.setDevicePixelRatio(ratio)
    return QIcon(pixmap)


def get_builtin_icon(
    name: str,
    size: Union[int, tuple] = 16,
    color: Union[str, None] = None,
) -> QIcon:
    """用内置图标名取 QIcon。name 可选：close, check, arrow_up, arrow_down, arrow_left, arrow_right, plus, minus。"""
    svg = BUILTIN_ICONS.get(name)
    if svg is None:
        return QIcon()
    return svg_to_icon(svg, size=size, color=color)
