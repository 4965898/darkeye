# design/loader.py - QSS 模板加载与令牌替换
from pathlib import Path

from .tokens import ThemeTokens


def load_stylesheet(template_path: Path, tokens: ThemeTokens) -> str:
    """读取 QSS 模板，将 {{token_name}} 替换为 tokens 中的值，返回最终样式表。"""
    raw = template_path.read_text(encoding="utf-8")
    for key, value in tokens.to_dict().items():
        raw = raw.replace("{{" + key + "}}", value)
    return raw
