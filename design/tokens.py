# design/tokens.py - 设计令牌定义与多套主题值
from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ThemeTokens:
    """一套主题对应的所有设计令牌。"""
    color_primary: str
    color_primary_hover: str
    color_bg: str
    color_bg_input: str
    color_bg_page: str
    color_border: str
    color_border_focus: str
    color_text: str
    color_text_placeholder: str
    color_text_disabled: str
    radius_md: str
    font_size_base: str
    border_width: str

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items()}


LIGHT_TOKENS = ThemeTokens(
    color_primary="#00aaff",
    color_primary_hover="#0099ee",
    color_bg="#ffffff",
    color_bg_input="#f0faff",
    color_bg_page="#f5f5f5",
    color_border="#ccc",
    color_border_focus="#00aaff",
    color_text="#333333",
    color_text_placeholder="#bbb",
    color_text_disabled="#999",
    radius_md="8px",
    font_size_base="12px",
    border_width="2px",
)

DARK_TOKENS = ThemeTokens(
    color_primary="#00aaff",
    color_primary_hover="#33bbff",
    color_bg="#1e1e1e",
    color_bg_input="#2d2d2d",
    color_bg_page="#252526",
    color_border="#444",
    color_border_focus="#00aaff",
    color_text="#e0e0e0",
    color_text_placeholder="#888",
    color_text_disabled="#666",
    radius_md="8px",
    font_size_base="12px",
    border_width="2px",
)
