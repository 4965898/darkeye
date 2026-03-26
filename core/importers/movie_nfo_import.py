"""Kodi 风格 <movie> NFO 解析并写入公有库 work 表。"""

from __future__ import annotations

import json
import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from controller.GlobalSignalBus import global_signals
from core.database.insert import (
    InsertNewLabel,
    InsertNewMaker,
    InsertNewSeries,
    InsertNewWorkByHand,
    insert_tag,
)
from core.database.query import get_tagid_by_keyword, get_workid_by_serialnumber
from core.database.query.work import (
    get_label_id_by_name,
    get_maker_id_by_name,
    get_series_id_by_name,
)


@dataclass
class ParsedMovieNfo:
    """仅含从 XML 读取的字段，不含数据库 id。"""

    serial_number: str
    jp_title: str
    jp_story: str
    director: str
    release_date: str | None
    runtime: int | None
    notes: str
    studio_raw: str
    genre_names: list[str]
    tag_names: list[str]  # 来自 <tag>，入库时解析为系列（首条非空）
    fanart_json: str | None


def _text(root: ET.Element, tag: str) -> str:
    node = root.find(tag)
    if node is None or node.text is None:
        return ""
    return node.text.strip()


def _parse_runtime(raw: str) -> int | None:
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None


def _collect_fanart_urls(movie: ET.Element) -> str | None:
    fan = movie.find("fanart")
    if fan is None:
        return None
    items: list[dict] = []
    for thumb in fan.findall("thumb"):
        url = (thumb.text or "").strip()
        if not url:
            url = (thumb.get("preview") or "").strip()
        if url:
            items.append({"url": url, "file": ""})
    if not items:
        return None
    return json.dumps(items, ensure_ascii=False)


def parse_movie_nfo(path: Path) -> tuple[ParsedMovieNfo | None, str | None]:
    """
    解析 NFO 文件（不访问数据库）。
    成功返回 (ParsedMovieNfo, None)，失败返回 (None, 错误信息)。
    """
    try:
        tree = ET.parse(path)
    except ET.ParseError as e:
        return None, f"XML 解析失败：{e}"
    except OSError as e:
        return None, f"无法读取文件：{e}"

    root = tree.getroot()
    if root is None or root.tag != "movie":
        return None, "根元素必须是 <movie>"

    serial = _text(root, "id") or _text(root, "num")
    serial = serial.strip()
    if not serial:
        return None, "NFO 中缺少番号（<id> 或 <num>）"

    premiered = _text(root, "premiered")
    release = _text(root, "release")
    release_date = (premiered or release) or None
    if release_date == "":
        release_date = None

    genre_names = [(g.text or "").strip() for g in root.findall("genre")]
    genre_names = [g for g in genre_names if g]
    tag_names = [(t.text or "").strip() for t in root.findall("tag")]
    tag_names = [t for t in tag_names if t]

    parsed = ParsedMovieNfo(
        serial_number=serial,
        jp_title=_text(root, "title"),
        jp_story=_text(root, "plot"),
        director=_text(root, "director"),
        release_date=release_date,
        runtime=_parse_runtime(_text(root, "runtime")),
        notes=_text(root, "source"),
        studio_raw=_text(root, "studio"),
        genre_names=genre_names,
        tag_names=tag_names,
        fanart_json=_collect_fanart_urls(root),
    )
    return parsed, None


def _resolve_maker_label(studio_raw: str) -> tuple[int | None, int | None, bool, bool]:
    maker_id: int | None = None
    label_id: int | None = None
    maker_added = False
    label_added = False
    if not studio_raw:
        return maker_id, label_id, maker_added, label_added
    parts = [p.strip() for p in studio_raw.split("/", 1)]
    maker_name = parts[0] if parts else ""
    label_name = parts[1].strip() if len(parts) > 1 else ""

    if maker_name:
        maker_id = get_maker_id_by_name(maker_name)
        if maker_id is None:
            maker_id = InsertNewMaker(maker_name)
            if maker_id is None:
                raise RuntimeError(f"创建片商失败：{maker_name}")
            maker_added = True

    if label_name:
        label_id = get_label_id_by_name(label_name)
        if label_id is None:
            label_id = InsertNewLabel(label_name)
            if label_id is None:
                raise RuntimeError(f"创建厂牌失败：{label_name}")
            label_added = True

    return maker_id, label_id, maker_added, label_added


def _resolve_series_from_nfo_tags(tag_names: list[str]) -> tuple[int | None, bool]:
    """NFO 的 <tag> 视为系列名：取首条非空，匹配或新建 series。"""
    series_name = ""
    for t in tag_names:
        s = (t or "").strip()
        if s:
            series_name = s
            break
    if not series_name:
        return None, False
    series_id = get_series_id_by_name(series_name)
    if series_id is not None:
        return series_id, False
    series_id = InsertNewSeries(series_name)
    if series_id is None:
        raise RuntimeError(f"创建系列失败：{series_name}")
    return series_id, True


def _resolve_tag_names(names: list[str]) -> tuple[list[int], bool]:
    tag_ids: list[int] = []
    seen: set[int] = set()
    tag_added = False
    for name in names:
        tid = get_tagid_by_keyword(name, match_hole_word=True)
        if tid:
            tid = int(tid)
        else:
            ok, _msg, tid = insert_tag(name, 11, "#cccccc", "", None, [])
            if not ok or tid is None:
                raise RuntimeError(f"创建标签失败：{name}")
            tag_added = True
        if tid not in seen:
            seen.add(tid)
            tag_ids.append(tid)
    return tag_ids, tag_added


def import_work_from_movie_nfo(path: Path) -> tuple[bool, str]:
    """
    从 NFO 导入一条作品。番号已存在则跳过写入。
    返回 (是否视为成功, 提示文案)。已跳过导入时返回 (False, 说明番号已存在)。
    """
    p = Path(path)
    if not p.is_file():
        return False, "不是有效的文件路径"

    parsed, err = parse_movie_nfo(p)
    if parsed is None:
        return False, err or "解析失败"

    if get_workid_by_serialnumber(parsed.serial_number) is not None:
        return False, f"番号「{parsed.serial_number}」已在库中，已跳过导入。"

    try:
        maker_id, label_id, maker_added, label_added = _resolve_maker_label(parsed.studio_raw)
        tag_ids, tag_added = _resolve_tag_names(list(dict.fromkeys(parsed.genre_names)))
        series_id, series_added = _resolve_series_from_nfo_tags(parsed.tag_names)
    except RuntimeError as e:
        return False, str(e)

    if maker_added:
        global_signals.maker_data_changed.emit()
    if label_added:
        global_signals.label_data_changed.emit()
    if series_added:
        global_signals.series_data_changed.emit()
    if tag_added:
        global_signals.tag_data_changed.emit()

    director = parsed.director.strip() or None
    jp_title = parsed.jp_title.strip() or None
    jp_story = parsed.jp_story.strip() or None
    notes = parsed.notes.strip() or None

    ok = InsertNewWorkByHand(
        parsed.serial_number,
        director,
        parsed.release_date,
        notes,
        parsed.runtime,
        [],
        [],
        None,
        None,
        jp_title,
        jp_story,
        None,
        tag_ids,
        maker_id,
        label_id,
        series_id,
        parsed.fanart_json,
    )
    if not ok:
        logging.warning("InsertNewWorkByHand failed for NFO import: %s", parsed.serial_number)
        return False, "写入数据库失败"

    global_signals.work_data_changed.emit()
    return True, f"已从 NFO 导入作品：{parsed.serial_number}"
