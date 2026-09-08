# -*- coding: utf-8 -*-
"""听小说 — Windows 真人神经网络语音听书应用"""

from __future__ import annotations

import asyncio
import ctypes
import hashlib
import json
import queue
import re
import threading
import time
from ctypes import wintypes
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
import edge_tts
import pygame

APP_NAME = "听小说"
APP_DIR = Path.home() / ".novel_listener"
PROGRESS_FILE = APP_DIR / "progress.json"
SETTINGS_FILE = APP_DIR / "settings.json"
LIBRARY_FILE = APP_DIR / "library.json"
CACHE_DIR = APP_DIR / "tts_cache"

NOVEL_FILETYPES = [
    ("支持的小说文件", "*.txt *.pdf *.doc *.docx *.epub *.rtf *.html *.htm *.md *.markdown *.text"),
    ("文本文件", "*.txt *.text *.md *.markdown"),
    ("PDF 文件", "*.pdf"),
    ("Word 文档", "*.doc *.docx"),
    ("电子书 EPUB", "*.epub"),
    ("网页 / RTF", "*.html *.htm *.rtf"),
    ("所有文件", "*.*"),
]
NOVEL_SUFFIXES = {
    ".txt",
    ".text",
    ".md",
    ".markdown",
    ".pdf",
    ".doc",
    ".docx",
    ".epub",
    ".rtf",
    ".html",
    ".htm",
}

# 日间 / 夜间 两套主题（保证文字与背景对比清晰）
THEMES: dict[str, dict[str, str]] = {
    "夜间": {
        "bg": "#0f0f0f",
        "sidebar": "#171717",
        "panel": "#1e1e1e",
        "panel_soft": "#2a2a2a",
        "reader": "#141414",
        "text": "#f5f5f5",
        "muted": "#b8b8b8",
        "faint": "#8c8c8c",
        "line": "#404040",
        "accent": "#5ecf8f",
        "accent_hover": "#76db9f",
        "accent_dim": "#1e3d2c",
        "on_accent": "#0a0a0a",
        "play": "#3d9b6e",
        "play_hover": "#4db580",
        "stop": "#d15a4e",
        "stop_hover": "#e06b5f",
        "chip": "#303030",
        "chip_hover": "#3c3c3c",
        "hit": "#4a4228",
        "hit_fg": "#ffe9b0",
        "hit_cur": "#e8b84a",
        "hit_cur_fg": "#1a1200",
        "speak": "#1b7a4a",
        "speak_fg": "#ffffff",
        "seg_text": "#ffffff",
        "seg_selected": "#3d9b6e",
        "seg_selected_hover": "#4db580",
        "seg_unselected": "#2a2a2a",
        "seg_unselected_hover": "#383838",
        "entry_bg": "#252525",
        "badge_idle": "#3a3a3a",
        "badge_idle_text": "#d0d0d0",
        "mode": "dark",
    },
    "日间": {
        "bg": "#eef0f2",
        "sidebar": "#e4e7eb",
        "panel": "#ffffff",
        "panel_soft": "#f3f4f6",
        "reader": "#ffffff",
        "text": "#111827",
        "muted": "#4b5563",
        "faint": "#6b7280",
        "line": "#c5cad3",
        "accent": "#15803d",
        "accent_hover": "#166534",
        "accent_dim": "#dcfce7",
        "on_accent": "#ffffff",
        "play": "#16a34a",
        "play_hover": "#15803d",
        "stop": "#dc2626",
        "stop_hover": "#b91c1c",
        "chip": "#e5e7eb",
        "chip_hover": "#d1d5db",
        "hit": "#fef3c7",
        "hit_fg": "#78350f",
        "hit_cur": "#f59e0b",
        "hit_cur_fg": "#1c1917",
        "speak": "#86efac",
        "speak_fg": "#14532d",
        "seg_text": "#111827",
        "seg_selected": "#86efac",
        "seg_selected_hover": "#4ade80",
        "seg_unselected": "#e5e7eb",
        "seg_unselected_hover": "#d1d5db",
        "entry_bg": "#ffffff",
        "badge_idle": "#d1d5db",
        "badge_idle_text": "#374151",
        "mode": "light",
    },
}
DEFAULT_THEME = "夜间"
THEME_NAMES = ["夜间", "日间"]


# 真人讲书音色：带讲述风格（mstts express-as），减少机械感
# (配置键, 显示名, Edge 语音 ID, 风格, 音调)
VOICE_PROFILES: list[tuple[str, str, str, str | None, str]] = [
    ("xiaoxiao_relaxed", "晓晓 · 轻松讲书（推荐）", "zh-CN-XiaoxiaoNeural", "narration-relaxed", "-2Hz"),
    ("xiaoxiao_pro", "晓晓 · 专业讲述", "zh-CN-XiaoxiaoNeural", "narration-professional", "+0Hz"),
    ("xiaoxiao_lyrical", "晓晓 · 抒情朗读", "zh-CN-XiaoxiaoNeural", "lyrical", "-1Hz"),
    ("xiaoxiao_gentle", "晓晓 · 温柔细语", "zh-CN-XiaoxiaoNeural", "gentle", "-3Hz"),
    ("yunyang_pro", "云扬 · 专业播讲", "zh-CN-YunyangNeural", "narration-professional", "-1Hz"),
    ("yunyang_news", "云扬 · 轻松播报", "zh-CN-YunyangNeural", "newscast-casual", "+0Hz"),
    ("yunxi_chat", "云希 · 沉稳聊天", "zh-CN-YunxiNeural", "chat", "-2Hz"),
    ("yunxi_calm", "云希 · 平静讲述", "zh-CN-YunxiNeural", "calm", "-2Hz"),
    ("xiaoyi", "晓伊 · 自然女声", "zh-CN-XiaoyiNeural", None, "-1Hz"),
    ("yunjian", "云健 · 自然男声", "zh-CN-YunjianNeural", None, "+0Hz"),
]
DEFAULT_VOICE_KEY = VOICE_PROFILES[0][0]


def get_voice_profile(key: str | None) -> tuple[str, str, str, str | None, str]:
    if key:
        for p in VOICE_PROFILES:
            if p[0] == key:
                return p
        # 兼容旧版只存了 voice ShortName
        for p in VOICE_PROFILES:
            if p[2] == key:
                return p
    return VOICE_PROFILES[0]


CHAPTER_PATTERNS = [
    re.compile(r"^\s*第[零一二三四五六七八九十百千万两〇\d]+[章节回卷部集].*$"),
    re.compile(r"^\s*Chapter\s+\d+.*$", re.IGNORECASE),
    re.compile(r"^\s*CHAPTER\s+[IVXLCDM]+.*$"),
    re.compile(r"^\s*[【\[]?\s*第?\s*\d+\s*[章节回卷]\s*[】\]]?.*$"),
    re.compile(r"^\s*[【\[]?(序章|楔子|引子|前言|序言|序|尾声|终章|番外|后记|附录).*$"),
]

SENTENCE_SPLIT = re.compile(r"(?<=[。！？!?；;…])\s*")


def clean_chapter_title(title: str) -> str:
    title = re.sub(r"\s+", " ", title.strip())
    title = title.strip("　 \t-—_·•")
    return title or "未命名章节"


def format_count(n: int) -> str:
    if n >= 10000:
        return f"{n / 10000:.1f}万字"
    return f"{n}字"


def ensure_app_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default):
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def save_json(path: Path, data) -> None:
    ensure_app_dir()
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def book_id_for_path(path: Path) -> str:
    try:
        key = str(path.resolve())
    except Exception:
        key = str(path)
    return hashlib.md5(key.encode("utf-8")).hexdigest()


def novel_display_title(path: Path) -> str:
    return path.stem.strip() or path.name


def is_novel_file(path: Path) -> bool:
    return path.suffix.lower() in NOVEL_SUFFIXES and (not path.exists() or path.is_file())


def load_library() -> dict:
    data = load_json(LIBRARY_FILE, {"books": [], "current_id": None})
    if not isinstance(data, dict):
        data = {"books": [], "current_id": None}
    books = data.get("books")
    if not isinstance(books, list):
        books = []
    cleaned = []
    seen = set()
    for item in books:
        if not isinstance(item, dict):
            continue
        p = str(item.get("path") or "").strip()
        if not p:
            continue
        path = Path(p)
        bid = str(item.get("id") or book_id_for_path(path))
        if bid in seen:
            continue
        seen.add(bid)
        cleaned.append(
            {
                "id": bid,
                "path": str(path),
                "title": str(item.get("title") or novel_display_title(path)),
                "added_at": float(item.get("added_at") or time.time()),
                "chapter_count": int(item.get("chapter_count") or 0),
                "char_count": int(item.get("char_count") or 0),
            }
        )
    data["books"] = cleaned
    data["current_id"] = data.get("current_id")
    return data


def save_library(data: dict) -> None:
    save_json(LIBRARY_FILE, data)


def read_text_file(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk", "big5"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")


def _normalize_extracted_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _html_to_text(html: str) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return soup.get_text("\n")


def read_pdf(path: Path) -> str:
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    parts: list[str] = []
    for page in reader.pages:
        try:
            t = page.extract_text() or ""
        except Exception:
            t = ""
        if t.strip():
            parts.append(t)
    text = "\n\n".join(parts)
    if not text.strip():
        raise ValueError("未能从 PDF 提取文字（可能是扫描版图片 PDF）")
    return text


def read_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    parts: list[str] = []
    for p in doc.paragraphs:
        if p.text.strip():
            parts.append(p.text)
    # 表格文字也读入
    for table in doc.tables:
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells if c.text.strip()]
            if cells:
                parts.append("\t".join(cells))
    text = "\n".join(parts)
    if not text.strip():
        raise ValueError("Word 文档中没有可提取的文字")
    return text


def read_doc(path: Path) -> str:
    """读取旧版 .doc：优先用本机 Word，其次尝试按 docx 打开。"""
    # 少数文件其实是 docx 改后缀
    try:
        return read_docx(path)
    except Exception:
        pass

    try:
        import win32com.client  # type: ignore
    except ImportError as exc:
        raise ValueError(
            "读取 .doc 需要安装 Microsoft Word，或请先另存为 .docx / .txt"
        ) from exc

    word = None
    doc = None
    try:
        word = win32com.client.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(str(path.resolve()), ReadOnly=True)
        text = doc.Content.Text
        # Word 常用 \r 作段落分隔
        text = text.replace("\r", "\n")
        if not text.strip():
            raise ValueError("Word 文档中没有可提取的文字")
        return text
    except Exception as exc:
        raise ValueError(
            f"无法读取 .doc 文件。请安装 Microsoft Word，或另存为 .docx/.txt。\n详情: {exc}"
        ) from exc
    finally:
        try:
            if doc is not None:
                doc.Close(False)
        except Exception:
            pass
        try:
            if word is not None:
                word.Quit()
        except Exception:
            pass


def read_epub(path: Path) -> str:
    from ebooklib import epub, ITEM_DOCUMENT
    from bs4 import BeautifulSoup

    book = epub.read_epub(str(path))
    parts: list[str] = []
    for item in book.get_items():
        if item.get_type() != ITEM_DOCUMENT:
            continue
        try:
            html = item.get_content().decode("utf-8", errors="ignore")
        except Exception:
            continue
        soup = BeautifulSoup(html, "lxml")
        t = soup.get_text("\n").strip()
        if t:
            parts.append(t)
    text = "\n\n".join(parts)
    if not text.strip():
        raise ValueError("未能从 EPUB 提取文字")
    return text


def read_rtf(path: Path) -> str:
    from striprtf.striprtf import rtf_to_text

    raw = path.read_bytes()
    for enc in ("utf-8", "gb18030", "latin-1"):
        try:
            rtf = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        rtf = raw.decode("utf-8", errors="ignore")
    text = rtf_to_text(rtf)
    if not text.strip():
        raise ValueError("未能从 RTF 提取文字")
    return text


def read_html(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            html = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        html = raw.decode("utf-8", errors="ignore")
    text = _html_to_text(html)
    if not text.strip():
        raise ValueError("未能从网页文件提取文字")
    return text


SUPPORTED_EXTENSIONS = {
    ".txt",
    ".text",
    ".md",
    ".markdown",
    ".pdf",
    ".docx",
    ".doc",
    ".epub",
    ".rtf",
    ".html",
    ".htm",
}


def read_document(path: Path) -> str:
    """按扩展名读取多种小说/电子书格式，统一返回纯文本。"""
    suffix = path.suffix.lower()
    if suffix in {".txt", ".text", ".md", ".markdown"}:
        text = read_text_file(path)
    elif suffix == ".pdf":
        text = read_pdf(path)
    elif suffix == ".docx":
        text = read_docx(path)
    elif suffix == ".doc":
        text = read_doc(path)
    elif suffix == ".epub":
        text = read_epub(path)
    elif suffix == ".rtf":
        text = read_rtf(path)
    elif suffix in {".html", ".htm"}:
        text = read_html(path)
    else:
        # 未知后缀：先当文本试读
        try:
            text = read_text_file(path)
        except Exception as exc:
            raise ValueError(
                f"暂不支持该格式：{suffix or '(无扩展名)'}\n"
                f"支持：txt / pdf / doc / docx / epub / rtf / html / md"
            ) from exc

    text = _normalize_extracted_text(text)
    if not text:
        raise ValueError("文件内容为空，或未能提取到文字")
    return text


def split_chapters(text: str) -> list[tuple[str, str]]:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    chapters: list[tuple[str, list[str]]] = []
    current_title = "正文"
    current_lines: list[str] = []

    for line in lines:
        if any(p.match(line.strip()) for p in CHAPTER_PATTERNS) and line.strip():
            if current_lines and "".join(current_lines).strip():
                chapters.append((current_title, current_lines))
            current_title = clean_chapter_title(line)[:120]
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines and "".join(current_lines).strip():
        chapters.append((clean_chapter_title(current_title), current_lines))

    if not chapters:
        return [("全文", text)]

    result: list[tuple[str, str]] = []
    for title, body_lines in chapters:
        body = "\n".join(body_lines).strip()
        if body:
            result.append((clean_chapter_title(title), body))
    return result or [("全文", text)]


def split_sentences(text: str) -> list[str]:
    parts = SENTENCE_SPLIT.split(text)
    return [p.strip() for p in parts if p and p.strip()]


def merge_speech_chunks(sentences: list[str], max_chars: int = 280) -> list[tuple[int, int, str]]:
    """把短句合并成朗读块，减少联网合成次数，听感更连贯。
    返回 (起始句下标, 结束句下标, 合并文本)。
    """
    if not sentences:
        return []
    chunks: list[tuple[int, int, str]] = []
    start = 0
    buf: list[str] = []
    size = 0
    for i, sent in enumerate(sentences):
        add = len(sent)
        if buf and size + add > max_chars:
            chunks.append((start, i - 1, "".join(buf)))
            start = i
            buf = [sent]
            size = add
        else:
            if not buf:
                start = i
            buf.append(sent)
            size += add
    if buf:
        chunks.append((start, start + len(buf) - 1, "".join(buf)))
    return chunks


def speed_to_rate(speed: float) -> str:
    """把 0.5~5.0 倍速转为 edge-tts rate 字符串。"""
    pct = int(round((speed - 1.0) * 100))
    return f"{pct:+d}%"


def speed_label(speed: float) -> str:
    return f"{speed:.1f}x"


def offset_to_sentence_index(body: str, offset: int) -> int:
    """根据正文绝对字符位置，定位到对应句子序号。"""
    sentences = split_sentences(body)
    if not sentences:
        return 0
    search_from = 0
    for i, sent in enumerate(sentences):
        idx = body.find(sent, search_from)
        if idx < 0:
            continue
        end = idx + len(sent)
        if idx <= offset < end:
            return i
        if offset < idx:
            return max(0, i - 1)
        search_from = end
    return max(0, len(sentences) - 1)


def find_all_offsets(text: str, query: str) -> list[int]:
    """不区分大小写查找全部出现位置。"""
    if not query:
        return []
    hay = text.lower()
    needle = query.lower()
    offsets: list[int] = []
    start = 0
    while True:
        pos = hay.find(needle, start)
        if pos < 0:
            break
        offsets.append(pos)
        start = pos + max(1, len(needle))
    return offsets


def build_sentence_spans(body: str, sentences: list[str]) -> list[tuple[int, int]]:
    """计算每句在正文中的字符起止位置，便于点击定位与高亮。"""
    spans: list[tuple[int, int]] = []
    search_from = 0
    for sent in sentences:
        if not sent:
            spans.append((search_from, search_from))
            continue
        idx = body.find(sent, search_from)
        if idx < 0:
            idx = body.find(sent)
        if idx < 0:
            spans.append((search_from, search_from))
            continue
        end = idx + len(sent)
        spans.append((idx, end))
        search_from = end
    return spans


def make_snippet(text: str, offset: int, query_len: int, radius: int = 18) -> str:
    left = max(0, offset - radius)
    right = min(len(text), offset + query_len + radius)
    snip = text[left:right].replace("\n", " ")
    if left > 0:
        snip = "…" + snip
    if right < len(text):
        snip = snip + "…"
    return snip


# —— 全局快捷键（可自定义）——
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_QUIT = 0x0012
HWND_MESSAGE = -3

VK_MAP: dict[str, int] = {
    "space": 0x20,
    "left": 0x25,
    "up": 0x26,
    "right": 0x27,
    "down": 0x28,
    "escape": 0x1B,
    "tab": 0x09,
    "return": 0x0D,
    "enter": 0x0D,
    "backspace": 0x08,
    "delete": 0x2E,
    "home": 0x24,
    "end": 0x23,
    "prior": 0x21,
    "next": 0x22,
    "plus": 0xBB,
    "equal": 0xBB,
    "minus": 0xBD,
    "media_play_pause": 0xB3,
    "media_stop": 0xB2,
    "media_prev_track": 0xB1,
    "media_next_track": 0xB0,
}
for _i, _ch in enumerate("ABCDEFGHIJKLMNOPQRSTUVWXYZ"):
    VK_MAP[_ch.lower()] = 0x41 + _i
for _i in range(10):
    VK_MAP[str(_i)] = 0x30 + _i
    VK_MAP[f"numpad{_i}"] = 0x60 + _i
for _i in range(1, 13):
    VK_MAP[f"f{_i}"] = 0x70 + _i - 1

HOTKEY_ACTIONS: list[tuple[str, str]] = [
    ("toggle_play", "播放 / 暂停"),
    ("stop", "停止"),
    ("prev_chapter", "上一章"),
    ("next_chapter", "下一章"),
    ("volume_up", "音量 +"),
    ("volume_down", "音量 −"),
    ("speed_up", "速度 +"),
    ("speed_down", "速度 −"),
    ("toggle_mini", "小窗切换"),
]

DEFAULT_HOTKEYS: dict[str, str] = {
    "toggle_play": "ctrl+alt+space",
    "stop": "ctrl+alt+s",
    "prev_chapter": "ctrl+alt+left",
    "next_chapter": "ctrl+alt+right",
    "volume_up": "ctrl+alt+up",
    "volume_down": "ctrl+alt+down",
    "speed_up": "ctrl+alt+equal",
    "speed_down": "ctrl+alt+minus",
    "toggle_mini": "ctrl+alt+m",
    # 媒体键（可选，空字符串表示禁用）
    "media_toggle_play": "media_play_pause",
    "media_stop": "media_stop",
    "media_prev": "media_prev_track",
    "media_next": "media_next_track",
}

MEDIA_ACTION_MAP = {
    "media_toggle_play": "toggle_play",
    "media_stop": "stop",
    "media_prev": "prev_chapter",
    "media_next": "next_chapter",
}


def normalize_hotkey(combo: str | None) -> str:
    if not combo:
        return ""
    parts = [p.strip().lower() for p in str(combo).replace("-", "+").split("+") if p.strip()]
    if not parts:
        return ""
    mods = []
    key = ""
    for p in parts:
        if p in ("ctrl", "control", "ctl"):
            if "ctrl" not in mods:
                mods.append("ctrl")
        elif p in ("alt", "menu"):
            if "alt" not in mods:
                mods.append("alt")
        elif p in ("shift",):
            if "shift" not in mods:
                mods.append("shift")
        else:
            key = p
    if not key:
        return ""
    # 统一别名
    aliases = {"return": "enter", "esc": "escape", "pgup": "prior", "pgdn": "next", "+": "equal", "=": "equal", "-": "minus"}
    key = aliases.get(key, key)
    return "+".join(mods + [key])


def parse_hotkey(combo: str) -> tuple[int, int] | None:
    """返回 (modifiers, vk)，失败返回 None。"""
    norm = normalize_hotkey(combo)
    if not norm:
        return None
    parts = norm.split("+")
    key = parts[-1]
    mods = 0
    for p in parts[:-1]:
        if p == "ctrl":
            mods |= MOD_CONTROL
        elif p == "alt":
            mods |= MOD_ALT
        elif p == "shift":
            mods |= MOD_SHIFT
    vk = VK_MAP.get(key)
    if vk is None and len(key) == 1:
        vk = ord(key.upper())
    if vk is None:
        return None
    # 媒体键可不带修饰键；普通键建议有修饰键，但仍允许注册
    return mods | MOD_NOREPEAT, vk


def format_hotkey_display(combo: str) -> str:
    norm = normalize_hotkey(combo)
    if not norm:
        return "未设置"
    mapping = {
        "ctrl": "Ctrl",
        "alt": "Alt",
        "shift": "Shift",
        "space": "空格",
        "left": "←",
        "right": "→",
        "up": "↑",
        "down": "↓",
        "equal": "+",
        "minus": "−",
        "media_play_pause": "媒体播放键",
        "media_stop": "媒体停止键",
        "media_prev_track": "媒体上一曲",
        "media_next_track": "媒体下一曲",
    }
    parts = []
    for p in norm.split("+"):
        parts.append(mapping.get(p, p.upper() if len(p) == 1 else p))
    return " + ".join(parts)


def merge_hotkeys(saved: dict | None) -> dict[str, str]:
    result = dict(DEFAULT_HOTKEYS)
    if isinstance(saved, dict):
        for k, v in saved.items():
            if k in result or k in MEDIA_ACTION_MAP or k in dict(HOTKEY_ACTIONS):
                result[k] = normalize_hotkey(v) if v else ""
    return result


def hotkeys_help_text(bindings: dict[str, str]) -> str:
    bits = []
    for action, label in HOTKEY_ACTIONS[:4]:
        combo = bindings.get(action, "")
        if combo:
            bits.append(f"{format_hotkey_display(combo)} {label}")
    return "快捷键：" + " · ".join(bits) if bits else "快捷键未设置"


class GlobalHotkeys:
    """系统级热键；动作放入队列，由主界面轮询执行。"""

    def __init__(self, bindings: dict[str, str] | None = None) -> None:
        self._q: queue.Queue[str] = queue.Queue()
        self._thread: threading.Thread | None = None
        self._tid: int | None = None
        self._hwnd = None
        self._ok = False
        self._actions: dict[int, str] = {}
        self._wnd_proc = None
        self.bindings = merge_hotkeys(bindings)
        self._pending_bindings: dict[str, str] | None = None

    @property
    def ready(self) -> bool:
        return self._ok

    def start(self, bindings: dict[str, str] | None = None) -> bool:
        if bindings is not None:
            self.bindings = merge_hotkeys(bindings)
        self.stop()
        self._pending_bindings = dict(self.bindings)
        self._thread = threading.Thread(target=self._run, daemon=True, name="global-hotkeys")
        self._thread.start()
        for _ in range(80):
            if self._ok or (self._thread and not self._thread.is_alive()):
                break
            time.sleep(0.02)
        return self._ok

    def stop(self) -> None:
        if self._tid is not None:
            try:
                ctypes.windll.user32.PostThreadMessageW(self._tid, WM_QUIT, 0, 0)
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self._thread = None
        self._ok = False
        self._actions.clear()

    def poll(self) -> list[str]:
        actions: list[str] = []
        while True:
            try:
                actions.append(self._q.get_nowait())
            except queue.Empty:
                break
        return actions

    def _register(self, hid: int, modifiers: int, vk: int, action: str) -> bool:
        if not ctypes.windll.user32.RegisterHotKey(self._hwnd, hid, modifiers, vk):
            return False
        self._actions[hid] = action
        return True

    def _run(self) -> None:
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32
        self._tid = threading.get_ident()

        LRESULT = ctypes.c_ssize_t
        WPARAM = ctypes.c_size_t
        LPARAM = ctypes.c_ssize_t
        WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT, WPARAM, LPARAM)

        user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, WPARAM, LPARAM]
        user32.DefWindowProcW.restype = LRESULT

        @WNDPROC
        def wnd_proc(hwnd, msg, wparam, lparam):
            if msg == WM_HOTKEY:
                action = self._actions.get(int(wparam))
                if action:
                    self._q.put(action)
                return 0
            return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

        self._wnd_proc = wnd_proc

        class WNDCLASSW(ctypes.Structure):
            _fields_ = [
                ("style", wintypes.UINT),
                ("lpfnWndProc", WNDPROC),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HANDLE),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
            ]

        hinst = kernel32.GetModuleHandleW(None)
        class_name = "NovelListenerHotkeyWnd"
        wc = WNDCLASSW()
        wc.style = 0
        wc.lpfnWndProc = wnd_proc
        wc.cbClsExtra = 0
        wc.cbWndExtra = 0
        wc.hInstance = hinst
        wc.hIcon = None
        wc.hCursor = None
        wc.hbrBackground = None
        wc.lpszMenuName = None
        wc.lpszClassName = class_name
        if not user32.RegisterClassW(ctypes.byref(wc)):
            err = kernel32.GetLastError()
            if err not in (0, 1410):
                return

        self._hwnd = user32.CreateWindowExW(
            0,
            class_name,
            "hotkey",
            0,
            0,
            0,
            0,
            0,
            wintypes.HWND(HWND_MESSAGE),
            None,
            hinst,
            None,
        )
        if not self._hwnd:
            return

        bindings = self._pending_bindings or self.bindings
        registered = 0
        hid = 1
        for key, combo in bindings.items():
            parsed = parse_hotkey(combo)
            if not parsed:
                continue
            mods, vk = parsed
            action = MEDIA_ACTION_MAP.get(key, key)
            if self._register(hid, mods, vk, action):
                registered += 1
            hid += 1
        self._ok = registered > 0

        msg = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            if msg.message == WM_HOTKEY:
                action = self._actions.get(int(msg.wParam))
                if action:
                    self._q.put(action)
            else:
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))

        for hid in list(self._actions):
            try:
                user32.UnregisterHotKey(self._hwnd, hid)
            except Exception:
                pass
        if self._hwnd:
            user32.DestroyWindow(self._hwnd)
        self._hwnd = None


class MiniControlWindow(ctk.CTkToplevel):
    """置顶迷你控制窗。"""

    def __init__(self, app: "App"):
        super().__init__(app)
        self.app = app
        self.title(f"{APP_NAME} · 小窗")
        self.geometry("380x148")
        self.resizable(False, False)
        try:
            self.attributes("-topmost", True)
        except Exception:
            pass
        self.configure(fg_color=app.theme["panel"])
        self.protocol("WM_DELETE_WINDOW", self._on_close_to_main)
        self._drag_x = 0
        self._drag_y = 0

        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=12, pady=10)

        head = ctk.CTkFrame(pad, fg_color="transparent")
        head.pack(fill="x")
        head.bind("<ButtonPress-1>", self._start_drag)
        head.bind("<B1-Motion>", self._on_drag)

        self.title_lbl = ctk.CTkLabel(
            head,
            text="未加载小说",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13, weight="bold"),
            text_color=app.theme["text"],
            anchor="w",
        )
        self.title_lbl.pack(side="left", fill="x", expand=True)
        self.title_lbl.bind("<ButtonPress-1>", self._start_drag)
        self.title_lbl.bind("<B1-Motion>", self._on_drag)

        ctk.CTkButton(
            head,
            text="展开",
            width=52,
            height=26,
            corner_radius=6,
            fg_color=app.theme["accent"],
            hover_color=app.theme["accent_hover"],
            text_color=app.theme["on_accent"],
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=11),
            command=app.exit_mini_mode,
        ).pack(side="right", padx=(8, 0))

        self.status_lbl = ctk.CTkLabel(
            pad,
            text="就绪",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=11),
            text_color=app.theme["muted"],
            anchor="w",
        )
        self.status_lbl.pack(fill="x", pady=(4, 8))

        row = ctk.CTkFrame(pad, fg_color="transparent")
        row.pack(fill="x")
        btn_kw = dict(
            height=36,
            corner_radius=8,
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13),
        )
        ctk.CTkButton(
            row,
            text="上一章",
            width=70,
            fg_color=app.theme["panel_soft"],
            hover_color=app.theme["chip"],
            text_color=app.theme["text"],
            command=app.prev_chapter,
            **btn_kw,
        ).pack(side="left", padx=(0, 4))
        self.btn_play = ctk.CTkButton(
            row,
            text="▶ 播放",
            width=96,
            fg_color=app.theme["play"],
            hover_color=app.theme["play_hover"],
            text_color="#fff",
            command=app.toggle_play,
            **btn_kw,
        )
        self.btn_play.pack(side="left", padx=4)
        ctk.CTkButton(
            row,
            text="停止",
            width=56,
            fg_color=app.theme["stop"],
            hover_color=app.theme["stop_hover"],
            text_color="#fff",
            command=app.stop_play,
            **btn_kw,
        ).pack(side="left", padx=4)
        ctk.CTkButton(
            row,
            text="下一章",
            width=70,
            fg_color=app.theme["panel_soft"],
            hover_color=app.theme["chip"],
            text_color=app.theme["text"],
            command=app.next_chapter,
            **btn_kw,
        ).pack(side="left", padx=4)

        ctk.CTkLabel(
            pad,
            text="可在主界面「快捷键」中自定义全局热键",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=10),
            text_color=app.theme["faint"],
            anchor="w",
        ).pack(fill="x", pady=(8, 0))

        self.refresh()
        self.after(80, self._place_near_corner)

    def _place_near_corner(self) -> None:
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            self.geometry(f"+{max(20, sw - 420)}+{max(20, sh - 220)}")
        except Exception:
            pass

    def _start_drag(self, event) -> None:
        self._drag_x = event.x_root - self.winfo_x()
        self._drag_y = event.y_root - self.winfo_y()

    def _on_drag(self, event) -> None:
        self.geometry(f"+{event.x_root - self._drag_x}+{event.y_root - self._drag_y}")

    def _on_close_to_main(self) -> None:
        self.app.exit_mini_mode()

    def refresh(self) -> None:
        app = self.app
        if app.chapters:
            title, _ = app.chapters[app.chapter_index]
            self.title_lbl.configure(text=f"{app.chapter_index + 1}/{len(app.chapters)} · {title[:22]}")
        elif app.file_path:
            self.title_lbl.configure(text=app.file_path.name)
        else:
            self.title_lbl.configure(text="未加载小说")

        if app.playing and not app.paused:
            self.btn_play.configure(text="⏸ 暂停")
        elif app.playing and app.paused:
            self.btn_play.configure(text="▶ 继续")
        else:
            self.btn_play.configure(text="▶ 播放")

        try:
            st = app.status_label.cget("text")
            if st:
                self.status_lbl.configure(text=str(st)[:48])
        except Exception:
            pass


class HotkeySettingsWindow(ctk.CTkToplevel):
    """自定义全局快捷键。"""

    def __init__(self, app: "App"):
        super().__init__(app)
        self.app = app
        self.title(f"{APP_NAME} · 快捷键设置")
        self.geometry("520x520")
        self.resizable(False, False)
        self.configure(fg_color=app.theme["bg"])
        self.transient(app)
        self.grab_set()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.draft = dict(app.hotkey_bindings)
        self._recording_action: str | None = None
        self._rows: dict[str, ctk.CTkLabel] = {}

        head = ctk.CTkLabel(
            self,
            text="点击「录制」后按下组合键（建议带 Ctrl/Alt）",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13),
            text_color=app.theme["muted"],
        )
        head.pack(fill="x", padx=16, pady=(14, 6))

        body = ctk.CTkScrollableFrame(self, fg_color=app.theme["panel"], corner_radius=12)
        body.pack(fill="both", expand=True, padx=16, pady=8)
        body.grid_columnconfigure(1, weight=1)

        for i, (action, label) in enumerate(HOTKEY_ACTIONS):
            ctk.CTkLabel(
                body,
                text=label,
                width=100,
                anchor="w",
                font=ctk.CTkFont(family="Microsoft YaHei UI", size=13),
                text_color=app.theme["text"],
            ).grid(row=i, column=0, padx=(10, 8), pady=6, sticky="w")
            val = ctk.CTkLabel(
                body,
                text=format_hotkey_display(self.draft.get(action, "")),
                anchor="w",
                font=ctk.CTkFont(family="Microsoft YaHei UI", size=12),
                text_color=app.theme["accent"],
            )
            val.grid(row=i, column=1, padx=4, pady=6, sticky="ew")
            self._rows[action] = val
            ctk.CTkButton(
                body,
                text="录制",
                width=56,
                height=28,
                fg_color=app.theme["panel_soft"],
                hover_color=app.theme["chip"],
                text_color=app.theme["text"],
                command=lambda a=action: self._start_record(a),
            ).grid(row=i, column=2, padx=4, pady=6)
            ctk.CTkButton(
                body,
                text="清除",
                width=56,
                height=28,
                fg_color=app.theme["panel_soft"],
                hover_color=app.theme["chip"],
                text_color=app.theme["muted"],
                command=lambda a=action: self._clear(a),
            ).grid(row=i, column=3, padx=(4, 10), pady=6)

        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.pack(fill="x", padx=16, pady=(4, 14))
        ctk.CTkButton(
            foot,
            text="恢复默认",
            width=100,
            fg_color=app.theme["panel_soft"],
            hover_color=app.theme["chip"],
            text_color=app.theme["text"],
            command=self._reset_defaults,
        ).pack(side="left")
        ctk.CTkButton(
            foot,
            text="取消",
            width=80,
            fg_color=app.theme["panel_soft"],
            hover_color=app.theme["chip"],
            text_color=app.theme["text"],
            command=self.destroy,
        ).pack(side="right", padx=(8, 0))
        ctk.CTkButton(
            foot,
            text="保存",
            width=90,
            fg_color=app.theme["play"],
            hover_color=app.theme["play_hover"],
            text_color="#fff",
            command=self._save,
        ).pack(side="right")

        self.bind("<KeyPress>", self._on_key)
        self.focus_force()

    def _refresh_row(self, action: str) -> None:
        if action in self._rows:
            self._rows[action].configure(text=format_hotkey_display(self.draft.get(action, "")))

    def _clear(self, action: str) -> None:
        self.draft[action] = ""
        self._recording_action = None
        self._refresh_row(action)

    def _reset_defaults(self) -> None:
        self.draft = merge_hotkeys(None)
        for action, _ in HOTKEY_ACTIONS:
            self._refresh_row(action)

    def _start_record(self, action: str) -> None:
        self._recording_action = action
        self._rows[action].configure(text="请按下快捷键…", text_color=self.app.theme["hit_cur"])
        self.focus_force()

    def _on_key(self, event) -> str | None:
        if not self._recording_action:
            return None
        keysym = (event.keysym or "").lower()
        if keysym in ("control_l", "control_r", "alt_l", "alt_r", "shift_l", "shift_r", "??"):
            return "break"
        parts = []
        state = int(event.state)
        if state & 0x4:
            parts.append("ctrl")
        if state & 0x20000 or state & 0x8:
            parts.append("alt")
        if state & 0x1:
            parts.append("shift")
        key = keysym
        aliases = {
            "return": "enter",
            "escape": "escape",
            "prior": "prior",
            "next": "next",
            "plus": "equal",
            "equal": "equal",
            "minus": "minus",
        }
        key = aliases.get(key, key)
        if key.startswith("kp_"):
            key = key[3:]
        combo = normalize_hotkey("+".join(parts + [key]))
        if not combo or parse_hotkey(combo) is None:
            self._rows[self._recording_action].configure(
                text="无法识别，请重试", text_color=self.app.theme["stop"]
            )
            return "break"
        # 查重
        for other, val in self.draft.items():
            if other != self._recording_action and normalize_hotkey(val) == combo:
                # 清除冲突项
                self.draft[other] = ""
                if other in self._rows:
                    self._refresh_row(other)
        action = self._recording_action
        self.draft[action] = combo
        self._recording_action = None
        self._rows[action].configure(
            text=format_hotkey_display(combo), text_color=self.app.theme["accent"]
        )
        return "break"

    def _save(self) -> None:
        # 保留媒体键配置
        for k, v in DEFAULT_HOTKEYS.items():
            if k.startswith("media_") and k not in self.draft:
                self.draft[k] = v
        self.app.apply_hotkey_bindings(self.draft)
        self.destroy()


class NeuralPlayer:
    """微软 Edge 神经网络真人讲书播放器（讲述风格 + 预加载）。"""

    PREFETCH = 3  # 提前合成几段，播放时不断档

    def __init__(self, on_status, on_sentence, on_finished):
        self.on_status = on_status
        self.on_sentence = on_sentence
        self.on_finished = on_finished
        self._stop = threading.Event()
        self._pause = threading.Event()
        self._pause.set()
        self._thread: threading.Thread | None = None
        self._producer: threading.Thread | None = None
        self._speed = 1.0
        self._voice_key = DEFAULT_VOICE_KEY
        self._voice_id = VOICE_PROFILES[0][2]
        self._style: str | None = VOICE_PROFILES[0][3]
        self._pitch = VOICE_PROFILES[0][4]
        self._volume = 1.0
        self._mixer_ready = False
        self._temp_files: list[Path] = []
        self._audio_q: queue.Queue | None = None

    def list_voices(self) -> list[tuple[str, str]]:
        return [(p[0], p[1]) for p in VOICE_PROFILES]

    def configure(self, speed: float, voice_key: str | None, volume: float) -> None:
        self._speed = max(0.5, min(5.0, float(speed)))
        if voice_key:
            key, _name, voice, style, pitch = get_voice_profile(voice_key)
            self._voice_key = key
            self._voice_id = voice
            self._style = style
            self._pitch = pitch
        self._volume = max(0.0, min(1.0, float(volume)))
        if self._mixer_ready:
            try:
                pygame.mixer.music.set_volume(self._volume)
            except Exception:
                pass

    def _ensure_mixer(self) -> None:
        if not self._mixer_ready:
            # 稍大缓冲，减少爆音/断续
            pygame.mixer.init(frequency=24000, size=-16, channels=1, buffer=4096)
            self._mixer_ready = True

    def _cache_path(self, text: str) -> Path:
        # v2：勿把整段 SSML 当正文传给 edge-tts（会被二次转义，朗读成标签）
        key = hashlib.md5(
            f"v2|{self._voice_key}|{self._pitch}|{speed_to_rate(self._speed)}|{text}".encode(
                "utf-8"
            )
        ).hexdigest()
        return CACHE_DIR / f"{key}.mp3"

    def play(self, sentences: list[str], start_index: int = 0) -> None:
        self.stop()
        self._stop.clear()
        self._pause.set()
        self._thread = threading.Thread(
            target=self._run,
            args=(sentences, start_index),
            daemon=True,
        )
        self._thread.start()

    def pause(self) -> None:
        self._pause.clear()
        try:
            if self._mixer_ready and pygame.mixer.music.get_busy():
                pygame.mixer.music.pause()
        except Exception:
            pass
        self.on_status("已暂停")

    def resume(self) -> None:
        self._pause.set()
        try:
            if self._mixer_ready:
                pygame.mixer.music.unpause()
        except Exception:
            pass
        self.on_status("播放中")

    def stop(self) -> None:
        self._stop.set()
        self._pause.set()
        try:
            if self._mixer_ready:
                pygame.mixer.music.stop()
        except Exception:
            pass
        # 解锁可能阻塞的队列
        if self._audio_q is not None:
            try:
                self._audio_q.put_nowait(None)
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.5)
        self._thread = None
        self._producer = None
        self._audio_q = None
        self._cleanup_temps()

    def _cleanup_temps(self) -> None:
        for path in self._temp_files:
            try:
                # 缓存文件保留，临时未入缓存的才删
                if path.parent == CACHE_DIR and len(path.stem) == 32:
                    continue
                path.unlink(missing_ok=True)
            except Exception:
                pass
        self._temp_files.clear()

    async def _synthesize(self, text: str, out_path: Path) -> None:
        # edge-tts 会自行包装 SSML；只能传纯文本，否则会朗读 XML 标签
        rate = speed_to_rate(self._speed)
        communicate = edge_tts.Communicate(
            text,
            voice=self._voice_id,
            rate=rate,
            pitch=self._pitch,
        )
        await communicate.save(str(out_path))
        if not out_path.exists() or out_path.stat().st_size <= 0:
            raise RuntimeError("语音文件为空，请检查网络后重试")

    def _prepare_audio(self, text: str, loop: asyncio.AbstractEventLoop) -> Path:
        cached = self._cache_path(text)
        if cached.exists() and cached.stat().st_size > 0:
            return cached
        loop.run_until_complete(self._synthesize(text, cached))
        return cached

    def _estimate_duration_ms(self, path: Path, text: str) -> int:
        try:
            dur = pygame.mixer.Sound(str(path)).get_length()
            if dur and dur > 0.2:
                return max(300, int(dur * 1000))
        except Exception:
            pass
        # 按字数粗估（约 4.5 字/秒，再按倍速缩放）
        cps = 4.5 * max(0.5, self._speed)
        return max(600, int(len(text) / cps * 1000))

    def _producer_loop(self, chunks: list[tuple[int, int, str]], audio_q: queue.Queue) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            for start_i, end_i, text in chunks:
                if self._stop.is_set():
                    break
                try:
                    path = self._prepare_audio(text, loop)
                    self._temp_files.append(path)
                    audio_q.put((start_i, end_i, text, path))
                except Exception as exc:
                    audio_q.put(("error", str(exc)))
                    return
            audio_q.put(None)
        finally:
            loop.close()

    def _run(self, sentences: list[str], start_index: int) -> None:
        try:
            self._ensure_mixer()
        except Exception as exc:
            self.on_status(f"音频初始化失败: {exc}")
            return

        # 从 start_index 起合并朗读块
        remaining = sentences[start_index:]
        if not remaining:
            self.on_finished()
            return
        raw_chunks = merge_speech_chunks(remaining, max_chars=90)
        # 把块内下标映射回全书句子下标
        chunks = [
            (start_index + a, start_index + b, text) for a, b, text in raw_chunks
        ]

        audio_q: queue.Queue = queue.Queue(maxsize=self.PREFETCH)
        self._audio_q = audio_q
        self.on_status("预加载语音中…")

        self._producer = threading.Thread(
            target=self._producer_loop, args=(chunks, audio_q), daemon=True
        )
        self._producer.start()

        finished_naturally = False
        try:
            while not self._stop.is_set():
                try:
                    item = audio_q.get(timeout=0.2)
                except queue.Empty:
                    if self._producer and not self._producer.is_alive():
                        break
                    continue

                if item is None:
                    finished_naturally = not self._stop.is_set()
                    break
                if isinstance(item, tuple) and item and item[0] == "error":
                    self.on_status(f"语音生成失败（需联网）: {item[1]}")
                    break

                start_i, end_i, text, path = item

                while not self._pause.is_set():
                    if self._stop.is_set():
                        break
                    time.sleep(0.05)
                if self._stop.is_set():
                    break

                # 先高亮块起点句
                self.on_sentence(start_i, start_i, sentences[start_i])
                self.on_status(f"播放中 · {start_i + 1}-{end_i + 1}/{len(sentences)}")

                duration_ms = self._estimate_duration_ms(path, text)
                weights = [max(1, len(sentences[i])) for i in range(start_i, end_i + 1)]
                total_w = float(sum(weights))
                last_sent = start_i

                try:
                    pygame.mixer.music.load(str(path))
                    pygame.mixer.music.set_volume(self._volume)
                    pygame.mixer.music.play()
                except Exception as exc:
                    self.on_status(f"播放失败: {exc}")
                    break

                while not self._stop.is_set():
                    if not self._pause.is_set():
                        time.sleep(0.05)
                        continue
                    if not pygame.mixer.music.get_busy():
                        break
                    # 按播放进度在朗读块内逐句推进高亮
                    try:
                        pos = pygame.mixer.music.get_pos()
                    except Exception:
                        pos = -1
                    if pos >= 0 and duration_ms > 0 and total_w > 0:
                        frac = min(0.999, max(0.0, pos / duration_ms))
                        target = frac * total_w
                        acc = 0.0
                        cur = start_i
                        for j, w in enumerate(weights):
                            acc += w
                            if target <= acc:
                                cur = start_i + j
                                break
                        if cur != last_sent:
                            last_sent = cur
                            self.on_sentence(cur, cur, sentences[cur])
                            self.on_status(f"播放中 · 句 {cur + 1}/{len(sentences)}")
                    time.sleep(0.04)

                if not self._stop.is_set() and last_sent != end_i:
                    self.on_sentence(end_i, end_i, sentences[end_i])

                if self._stop.is_set():
                    try:
                        pygame.mixer.music.stop()
                    except Exception:
                        pass
                    break

            if finished_naturally:
                self.on_finished()
            elif self._stop.is_set():
                self.on_status("已停止")
        finally:
            self._stop.set()
            if self._producer and self._producer.is_alive():
                self._producer.join(timeout=1.0)
            self._producer = None
            self._audio_q = None
            # 不清理缓存 mp3，加速重复收听
            self._temp_files = [p for p in self._temp_files if not (p.parent == CACHE_DIR and len(p.stem) == 32)]
            self._cleanup_temps()


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ensure_app_dir()

        settings = load_json(SETTINGS_FILE, {})
        self.theme_name = settings.get("theme", DEFAULT_THEME)
        # 兼容旧版多主题名称
        if self.theme_name not in THEMES:
            if self.theme_name in ("素纸日光", "日间", "白色", "light"):
                self.theme_name = "日间"
            else:
                self.theme_name = DEFAULT_THEME
        self.theme = THEMES[self.theme_name]

        self.title(APP_NAME)
        self.geometry("1120x760")
        self.minsize(960, 640)
        self.configure(fg_color=self.theme["bg"])
        ctk.set_appearance_mode(self.theme.get("mode", "dark"))
        ctk.set_default_color_theme("dark-blue")

        self.font_title = ctk.CTkFont(family="Microsoft YaHei UI", size=22, weight="bold")
        self.font_h = ctk.CTkFont(family="Microsoft YaHei UI", size=16, weight="bold")
        self.font_body = ctk.CTkFont(family="Microsoft YaHei UI", size=15)
        self.font_ui = ctk.CTkFont(family="Microsoft YaHei UI", size=13)
        self.font_small = ctk.CTkFont(family="Microsoft YaHei UI", size=11)
        self.font_reader = ctk.CTkFont(family="Microsoft YaHei UI", size=16)

        self.file_path: Path | None = None
        self.chapters: list[tuple[str, str]] = []
        self.chapter_index = 0
        self.sentences: list[str] = []
        self.sentence_index = 0
        self.playing = False
        self.paused = False
        self._chapter_rows: dict[int, ctk.CTkFrame] = {}
        self._book_rows: dict[str, ctk.CTkFrame] = {}
        self._chapter_filter = ""
        self._sidebar_mode = "目录"  # 书架 / 目录
        self.library = load_library()
        self.current_book_id: str | None = self.library.get("current_id")
        self.content_matches: list[tuple[int, int, int, str]] = []
        self.content_match_index = -1
        self._content_query = ""
        self._search_scope = "全书"
        self._sentence_spans: list[tuple[int, int]] = []
        self._progress_seek_job: str | None = None
        self._progress_dragging = False
        self._suppress_progress_event = False
        self._reader_click_job: str | None = None
        self.hotkey_bindings = merge_hotkeys(settings.get("hotkeys"))
        self._play_ui_q: queue.Queue = queue.Queue()

        # 兼容旧版 rate(100-300) 与新版 speed(0.5-5.0)
        if "speed" in settings:
            self.speed_value = max(0.5, min(5.0, float(settings.get("speed", 1.0))))
        else:
            old_rate = settings.get("rate")
            if old_rate is not None:
                self.speed_value = max(0.5, min(5.0, float(old_rate) / 180.0))
            else:
                self.speed_value = 1.0
        self.volume_value = float(settings.get("volume", 1.0))
        self.voice_id = settings.get("voice_id") or DEFAULT_VOICE_KEY
        # 规范化为配置键
        self.voice_id = get_voice_profile(self.voice_id)[0]

        self.player = NeuralPlayer(
            on_status=self._ui_status,
            on_sentence=self._ui_sentence,
            on_finished=self._ui_finished,
        )
        self.voices = self.player.list_voices()
        if not any(vid == self.voice_id for vid, _ in self.voices):
            self.voice_id = self.voices[0][0]

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.mini: MiniControlWindow | None = None
        self._mini_mode = False
        self.hotkeys = GlobalHotkeys(self.hotkey_bindings)
        self._hotkey_win: HotkeySettingsWindow | None = None
        self.after(200, self._try_restore_last)
        self.after(300, self._start_hotkeys)
        self.after(50, self._drain_play_ui)

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # —— 左侧：品牌 + 导入 + 书架/目录 ——
        sidebar = ctk.CTkFrame(self, width=332, corner_radius=0, fg_color=self.theme["sidebar"])
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(5, weight=1)

        brand = ctk.CTkFrame(sidebar, fg_color="transparent")
        brand.grid(row=0, column=0, sticky="ew", padx=18, pady=(22, 8))
        ctk.CTkLabel(brand, text=APP_NAME, font=self.font_title, text_color=self.theme["text"], anchor="w").pack(
            anchor="w"
        )
        ctk.CTkLabel(
            brand,
            text="真人讲书 · 多本书架",
            font=self.font_small,
            text_color=self.theme["muted"],
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        import_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        import_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(8, 8))
        import_row.grid_columnconfigure(0, weight=1)
        import_row.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            import_row,
            text="导入小说",
            height=36,
            corner_radius=10,
            font=self.font_ui,
            fg_color=self.theme["accent"],
            hover_color=self.theme["accent_hover"],
            text_color=self.theme["on_accent"],
            command=self.import_novels,
        ).grid(row=0, column=0, sticky="ew", padx=(4, 4))
        ctk.CTkButton(
            import_row,
            text="导入文件夹",
            height=36,
            corner_radius=10,
            font=self.font_ui,
            fg_color=self.theme["panel_soft"],
            hover_color=self.theme["chip"],
            text_color=self.theme["text"],
            command=self.import_folder,
        ).grid(row=0, column=1, sticky="ew", padx=(4, 4))

        self.sidebar_mode = ctk.CTkSegmentedButton(
            sidebar,
            values=["书架", "目录"],
            height=32,
            font=self.font_small,
            selected_color=self.theme["seg_selected"],
            selected_hover_color=self.theme["seg_selected_hover"],
            unselected_color=self.theme["seg_unselected"],
            unselected_hover_color=self.theme["seg_unselected_hover"],
            text_color=self.theme["seg_text"],
            command=self._on_sidebar_mode,
        )
        self.sidebar_mode.set(self._sidebar_mode if self._sidebar_mode in ("书架", "目录") else "目录")
        self.sidebar_mode.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 8))

        catalog_head = ctk.CTkFrame(sidebar, fg_color="transparent")
        catalog_head.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 6))
        catalog_head.grid_columnconfigure(0, weight=1)
        self.sidebar_section_label = ctk.CTkLabel(
            catalog_head, text="目录", font=self.font_h, text_color=self.theme["text"], anchor="w"
        )
        self.sidebar_section_label.grid(row=0, column=0, sticky="w")
        self.catalog_count_label = ctk.CTkLabel(
            catalog_head, text="未加载", font=self.font_small, text_color=self.theme["faint"], anchor="e"
        )
        self.catalog_count_label.grid(row=0, column=1, sticky="e")

        search_row = ctk.CTkFrame(sidebar, fg_color="transparent")
        search_row.grid(row=4, column=0, sticky="ew", padx=14, pady=(0, 8))
        search_row.grid_columnconfigure(0, weight=1)
        self.chapter_search = ctk.CTkEntry(
            search_row,
            placeholder_text="筛选章节 / 书名…",
            height=34,
            corner_radius=8,
            border_width=1,
            border_color=self.theme["line"],
            fg_color=self.theme["entry_bg"],
            text_color=self.theme["text"],
            placeholder_text_color=self.theme["faint"],
            font=self.font_ui,
        )
        self.chapter_search.grid(row=0, column=0, sticky="ew", padx=(4, 6))
        self.chapter_search.bind("<KeyRelease>", self._on_sidebar_search)
        self.btn_sidebar_action = ctk.CTkButton(
            search_row,
            text="定位",
            width=52,
            height=34,
            corner_radius=8,
            fg_color=self.theme["panel_soft"],
            hover_color=self.theme["chip"],
            text_color=self.theme["text"],
            font=self.font_small,
            command=self._sidebar_action,
        )
        self.btn_sidebar_action.grid(row=0, column=1, padx=(0, 4))

        self.chapter_list = ctk.CTkScrollableFrame(
            sidebar,
            label_text="",
            fg_color=self.theme["panel"],
            corner_radius=12,
            border_width=0,
            scrollbar_button_color=self.theme["chip"],
            scrollbar_button_hover_color=self.theme["accent"],
        )
        self.chapter_list.grid(row=5, column=0, padx=12, pady=(0, 14), sticky="nsew")
        self._refresh_sidebar_list()

        # —— 右侧主区域 ——
        main = ctk.CTkFrame(self, corner_radius=0, fg_color=self.theme["bg"])
        main.grid(row=0, column=1, sticky="nsew", padx=(0, 0), pady=0)
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)

        # 顶栏：章节信息
        top = ctk.CTkFrame(main, fg_color=self.theme["bg"], height=72)
        top.grid(row=0, column=0, sticky="ew", padx=22, pady=(18, 4))
        top.grid_columnconfigure(0, weight=1)
        self.title_label = ctk.CTkLabel(
            top,
            text="打开一本小说，开始收听",
            font=self.font_h,
            text_color=self.theme["text"],
            anchor="w",
        )
        self.title_label.grid(row=0, column=0, sticky="w")
        self.file_label = ctk.CTkLabel(
            top, text="支持 txt / pdf / doc / docx / epub 等", font=self.font_small, text_color=self.theme["muted"], anchor="w"
        )
        self.file_label.grid(row=1, column=0, sticky="w", pady=(2, 0))

        # 搜索工具条
        search_bar = ctk.CTkFrame(main, fg_color=self.theme["panel"], corner_radius=12)
        search_bar.grid(row=1, column=0, sticky="ew", padx=22, pady=(8, 10))
        search_bar.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            search_bar, text="正文", font=self.font_ui, text_color=self.theme["muted"]
        ).grid(row=0, column=0, padx=(14, 8), pady=10)
        self.content_search_entry = ctk.CTkEntry(
            search_bar,
            placeholder_text="搜索正文关键词，定位到对应位置…",
            height=34,
            corner_radius=8,
            border_width=1,
            border_color=self.theme["line"],
            fg_color=self.theme["entry_bg"],
            text_color=self.theme["text"],
            placeholder_text_color=self.theme["faint"],
            font=self.font_ui,
        )
        self.content_search_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=10)
        self.content_search_entry.bind("<Return>", lambda _e: self.search_content())

        self.search_scope = ctk.CTkSegmentedButton(
            search_bar,
            values=["全书", "本章"],
            width=110,
            height=32,
            font=self.font_small,
            selected_color=self.theme["seg_selected"],
            selected_hover_color=self.theme["seg_selected_hover"],
            unselected_color=self.theme["seg_unselected"],
            unselected_hover_color=self.theme["seg_unselected_hover"],
            text_color=self.theme["seg_text"],
            command=self._on_search_scope,
        )
        self.search_scope.set("全书")
        self.search_scope.grid(row=0, column=2, padx=6, pady=10)

        for i, (label, cmd) in enumerate(
            [
                ("搜索", self.search_content),
                ("上一个", lambda: self.goto_content_match(-1)),
                ("下一个", lambda: self.goto_content_match(1)),
            ]
        ):
            ctk.CTkButton(
                search_bar,
                text=label,
                width=64,
                height=32,
                corner_radius=8,
                fg_color=self.theme["panel_soft"],
                hover_color=self.theme["chip"],
                text_color=self.theme["text"],
                font=self.font_small,
                command=cmd,
            ).grid(row=0, column=3 + i, padx=3, pady=10)

        ctk.CTkButton(
            search_bar,
            text="从此处播放",
            width=96,
            height=32,
            corner_radius=8,
            fg_color=self.theme["play"],
            hover_color=self.theme["play_hover"],
            text_color="#fff",
            font=self.font_small,
            command=self.play_from_match,
        ).grid(row=0, column=6, padx=(6, 8), pady=10)

        self.content_match_label = ctk.CTkLabel(
            search_bar, text="", width=64, font=self.font_small, text_color=self.theme["accent"]
        )
        self.content_match_label.grid(row=0, column=7, padx=(0, 12), pady=10)

        # 阅读区
        reader_wrap = ctk.CTkFrame(main, fg_color=self.theme["panel"], corner_radius=14)
        reader_wrap.grid(row=2, column=0, sticky="nsew", padx=22, pady=(0, 10))
        reader_wrap.grid_columnconfigure(0, weight=1)
        reader_wrap.grid_rowconfigure(0, weight=1)

        self.text_box = ctk.CTkTextbox(
            reader_wrap,
            wrap="word",
            font=self.font_reader,
            fg_color=self.theme["reader"],
            text_color=self.theme["text"],
            corner_radius=12,
            border_width=0,
            activate_scrollbars=True,
            scrollbar_button_color=self.theme["chip"],
            scrollbar_button_hover_color=self.theme["accent"],
        )
        self.text_box.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 4))
        self._set_reader_text(
            "欢迎使用听小说\n\n"
            "1. 左侧「导入小说」可一次加入多本，或「导入文件夹」批量添加\n"
            "2. 在「书架」里点选要听的书；「目录」里跳转章节\n"
            "3. 底部选择「讲书音色」，点播放开始收听\n"
            "4. 单击正文可从该位置开始听；拖动进度条可跳转\n\n"
            "朗读时正文会高亮并自动跟随滚动。"
        )
        self._setup_reader_readonly()
        try:
            self.text_box._textbox.bind("<ButtonRelease-1>", self._on_reader_click, add="+")
            self.text_box._textbox.bind("<Double-Button-1>", self._on_reader_double_click, add="+")
        except Exception:
            self.text_box.bind("<ButtonRelease-1>", self._on_reader_click, add="+")
            self.text_box.bind("<Double-Button-1>", self._on_reader_double_click, add="+")

        self.progress_bar = ctk.CTkFrame(reader_wrap, fg_color="transparent")
        self.progress_bar.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.progress_bar.grid_columnconfigure(1, weight=1)
        self.progress_label = ctk.CTkLabel(
            self.progress_bar,
            text="进度 —",
            width=88,
            anchor="w",
            font=self.font_small,
            text_color=self.theme["muted"],
        )
        self.progress_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        self.progress_slider = ctk.CTkSlider(
            self.progress_bar,
            from_=0,
            to=1,
            number_of_steps=1,
            progress_color=self.theme["accent"],
            button_color=self.theme["accent"],
            button_hover_color=self.theme["accent_hover"],
            fg_color=self.theme["chip"],
            command=self._on_progress_drag,
        )
        self.progress_slider.set(0)
        self.progress_slider.grid(row=0, column=1, sticky="ew")
        self.progress_pct_label = ctk.CTkLabel(
            self.progress_bar,
            text="0%",
            width=42,
            anchor="e",
            font=self.font_small,
            text_color=self.theme["muted"],
        )
        self.progress_pct_label.grid(row=0, column=2, sticky="e", padx=(8, 0))
        self._bind_progress_slider_release()

        # 播放控制条（核心操作，置中放大）
        dock = ctk.CTkFrame(main, fg_color=self.theme["panel"], corner_radius=14)
        dock.grid(row=3, column=0, sticky="ew", padx=22, pady=(0, 10))
        dock.grid_columnconfigure(0, weight=1)
        dock.grid_columnconfigure(1, weight=0)
        dock.grid_columnconfigure(2, weight=1)

        self.status_label = ctk.CTkLabel(
            dock, text="就绪", font=self.font_small, text_color=self.theme["muted"], anchor="w"
        )
        self.status_label.grid(row=0, column=0, sticky="w", padx=16, pady=14)

        transport = ctk.CTkFrame(dock, fg_color="transparent")
        transport.grid(row=0, column=1, pady=10)

        btn_sec = dict(
            width=88,
            height=40,
            corner_radius=10,
            fg_color=self.theme["panel_soft"],
            hover_color=self.theme["chip"],
            text_color=self.theme["text"],
            font=self.font_ui,
        )
        self.btn_prev = ctk.CTkButton(transport, text="上一章", command=self.prev_chapter, **btn_sec)
        self.btn_prev.pack(side="left", padx=4)
        self.btn_play = ctk.CTkButton(
            transport,
            text="▶  播放",
            width=120,
            height=44,
            corner_radius=12,
            fg_color=self.theme["play"],
            hover_color=self.theme["play_hover"],
            text_color="#fff",
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=15, weight="bold"),
            command=self.toggle_play,
        )
        self.btn_play.pack(side="left", padx=8)
        self.btn_stop = ctk.CTkButton(
            transport,
            text="停止",
            width=72,
            height=40,
            corner_radius=10,
            fg_color=self.theme["stop"],
            hover_color=self.theme["stop_hover"],
            text_color="#fff",
            font=self.font_ui,
            command=self.stop_play,
        )
        self.btn_stop.pack(side="left", padx=4)
        self.btn_next = ctk.CTkButton(transport, text="下一章", command=self.next_chapter, **btn_sec)
        self.btn_next.pack(side="left", padx=4)
        self.btn_mini = ctk.CTkButton(
            transport,
            text="小窗",
            width=64,
            height=40,
            corner_radius=10,
            fg_color=self.theme["accent_dim"],
            hover_color=self.theme["chip"],
            text_color=self.theme["accent"],
            font=self.font_ui,
            command=self.enter_mini_mode,
        )
        self.btn_mini.pack(side="left", padx=(12, 4))

        self.speed_label = ctk.CTkLabel(
            dock, text=speed_label(self.speed_value), font=self.font_ui, text_color=self.theme["accent"], width=56, anchor="e"
        )
        self.speed_label.grid(row=0, column=2, sticky="e", padx=16, pady=14)

        # 设置条：速度 / 音量 / 音色 一行化
        settings = ctk.CTkFrame(main, fg_color=self.theme["panel"], corner_radius=14)
        settings.grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 18))
        settings.grid_columnconfigure(1, weight=2)
        settings.grid_columnconfigure(3, weight=1)
        settings.grid_columnconfigure(5, weight=1)

        ctk.CTkLabel(settings, text="速度", font=self.font_small, text_color=self.theme["muted"]).grid(
            row=0, column=0, padx=(16, 6), pady=(14, 4), sticky="w"
        )
        speed_row = ctk.CTkFrame(settings, fg_color="transparent")
        speed_row.grid(row=0, column=1, sticky="ew", padx=4, pady=(12, 2))
        speed_row.grid_columnconfigure(2, weight=1)

        nudge_kw = dict(
            width=32,
            height=28,
            corner_radius=6,
            fg_color=self.theme["panel_soft"],
            hover_color=self.theme["chip"],
            text_color=self.theme["text"],
            font=self.font_ui,
        )
        self.btn_speed_down = ctk.CTkButton(speed_row, text="−", command=lambda: self._nudge_speed(-0.1), **nudge_kw)
        self.btn_speed_down.grid(row=0, column=0, padx=(0, 4))
        self.speed_presets = ctk.CTkSegmentedButton(
            speed_row,
            values=["1.0x", "1.5x", "2.0x", "3.0x", "5.0x"],
            height=28,
            font=self.font_small,
            selected_color=self.theme["seg_selected"],
            selected_hover_color=self.theme["seg_selected_hover"],
            unselected_color=self.theme["seg_unselected"],
            unselected_hover_color=self.theme["seg_unselected_hover"],
            text_color=self.theme["seg_text"],
            command=self._on_speed_preset,
        )
        self.speed_presets.grid(row=0, column=1, padx=4)
        self.speed_slider = ctk.CTkSlider(
            speed_row,
            from_=0.5,
            to=5.0,
            number_of_steps=45,
            progress_color=self.theme["accent"],
            button_color=self.theme["accent"],
            button_hover_color=self.theme["accent_hover"],
            fg_color=self.theme["chip"],
            command=self._on_speed,
        )
        self.speed_slider.set(self.speed_value)
        self.speed_slider.grid(row=0, column=2, sticky="ew", padx=8)
        self.btn_speed_up = ctk.CTkButton(speed_row, text="+", command=lambda: self._nudge_speed(0.1), **nudge_kw)
        self.btn_speed_up.grid(row=0, column=3)

        ctk.CTkLabel(settings, text="音量", font=self.font_small, text_color=self.theme["muted"]).grid(
            row=0, column=2, padx=(12, 6), pady=(14, 4), sticky="w"
        )
        vol_box = ctk.CTkFrame(settings, fg_color="transparent")
        vol_box.grid(row=0, column=3, sticky="ew", padx=4, pady=(12, 2))
        vol_box.grid_columnconfigure(0, weight=1)
        self.vol_slider = ctk.CTkSlider(
            vol_box,
            from_=0,
            to=1,
            number_of_steps=20,
            progress_color=self.theme["accent"],
            button_color=self.theme["accent"],
            button_hover_color=self.theme["accent_hover"],
            fg_color=self.theme["chip"],
            command=self._on_volume,
        )
        self.vol_slider.set(self.volume_value)
        self.vol_slider.grid(row=0, column=0, sticky="ew")
        self.vol_label = ctk.CTkLabel(
            vol_box, text=f"{int(self.volume_value * 100)}%", width=42, font=self.font_small, text_color=self.theme["muted"]
        )
        self.vol_label.grid(row=0, column=1, padx=(6, 0))

        ctk.CTkLabel(settings, text="讲书音色", font=self.font_small, text_color=self.theme["muted"]).grid(
            row=0, column=4, padx=(12, 6), pady=(14, 4), sticky="w"
        )
        voice_names = [name for _, name in self.voices]
        self.voice_menu = ctk.CTkOptionMenu(
            settings,
            values=voice_names,
            height=32,
            corner_radius=8,
            fg_color=self.theme["panel_soft"],
            button_color=self.theme["chip"],
            button_hover_color=self.theme["accent"],
            text_color=self.theme["text"],
            font=self.font_small,
            dropdown_fg_color=self.theme["panel"],
            dropdown_hover_color=self.theme["chip"],
            dropdown_text_color=self.theme["text"],
            command=self._on_voice,
        )
        self.voice_menu.grid(row=0, column=5, sticky="ew", padx=(4, 16), pady=(12, 2))
        selected_name = next((n for v, n in self.voices if v == self.voice_id), voice_names[0])
        self.voice_menu.set(selected_name)

        # 第二行：日间 / 夜间
        ctk.CTkLabel(settings, text="主题", font=self.font_small, text_color=self.theme["muted"]).grid(
            row=1, column=0, padx=(16, 6), pady=(4, 12), sticky="w"
        )
        theme_row = ctk.CTkFrame(settings, fg_color="transparent")
        theme_row.grid(row=1, column=1, columnspan=5, sticky="w", padx=(4, 16), pady=(4, 12))

        self.btn_theme_night = ctk.CTkButton(
            theme_row,
            text="夜间 · 黑",
            width=100,
            height=34,
            corner_radius=8,
            font=self.font_ui,
            command=lambda: self._on_theme_change("夜间"),
        )
        self.btn_theme_night.pack(side="left", padx=(0, 8))
        self.btn_theme_day = ctk.CTkButton(
            theme_row,
            text="日间 · 白",
            width=100,
            height=34,
            corner_radius=8,
            font=self.font_ui,
            command=lambda: self._on_theme_change("日间"),
        )
        self.btn_theme_day.pack(side="left")
        self._refresh_theme_buttons()

        ctk.CTkButton(
            theme_row,
            text="快捷键",
            width=72,
            height=34,
            corner_radius=8,
            font=self.font_ui,
            fg_color=self.theme["panel_soft"],
            hover_color=self.theme["chip"],
            text_color=self.theme["text"],
            command=self.open_hotkey_settings,
        ).pack(side="left", padx=(12, 0))

        self.hotkey_tip = ctk.CTkLabel(
            theme_row,
            text=hotkeys_help_text(self.hotkey_bindings),
            font=self.font_small,
            text_color=self.theme["faint"],
            anchor="w",
        )
        self.hotkey_tip.pack(side="left", padx=(12, 0))

        self._sync_speed_preset()
        self.player.configure(self.speed_value, self.voice_id, self.volume_value)

    def _refresh_theme_buttons(self) -> None:
        if not hasattr(self, "btn_theme_night"):
            return
        night_on = self.theme_name == "夜间"
        self.btn_theme_night.configure(
            fg_color=self.theme["accent"] if night_on else self.theme["panel_soft"],
            hover_color=self.theme["accent_hover"] if night_on else self.theme["chip"],
            text_color=self.theme["on_accent"] if night_on else self.theme["text"],
            border_width=0 if night_on else 1,
            border_color=self.theme["line"],
        )
        self.btn_theme_day.configure(
            fg_color=self.theme["accent"] if not night_on else self.theme["panel_soft"],
            hover_color=self.theme["accent_hover"] if not night_on else self.theme["chip"],
            text_color=self.theme["on_accent"] if not night_on else self.theme["text"],
            border_width=0 if not night_on else 1,
            border_color=self.theme["line"],
        )

    def _sync_speed_preset(self) -> None:
        key = f"{self.speed_value:.1f}x"
        presets = ("1.0x", "1.5x", "2.0x", "3.0x", "5.0x")
        if key in presets:
            self.speed_presets.set(key)
        else:
            nearest = min([1.0, 1.5, 2.0, 3.0, 5.0], key=lambda x: abs(x - self.speed_value))
            self.speed_presets.set(f"{nearest:.1f}x")

    def _set_speed(self, value: float, restart_hint: bool = True) -> None:
        self.speed_value = round(max(0.5, min(5.0, float(value))), 1)
        self.speed_slider.set(self.speed_value)
        self.speed_label.configure(text=speed_label(self.speed_value))
        self._sync_speed_preset()
        self.player.configure(self.speed_value, self.voice_id, self.volume_value)
        self._save_settings_only()
        if restart_hint and self.playing and not self.paused:
            self._ui_status(f"速度已设为 {speed_label(self.speed_value)}（下一句生效）")

    def _on_speed(self, value) -> None:
        self._set_speed(float(value))

    def _on_speed_preset(self, label: str) -> None:
        try:
            self._set_speed(float(label.replace("x", "")))
        except ValueError:
            pass

    def _nudge_speed(self, delta: float) -> None:
        self._set_speed(self.speed_value + delta)

    def _clear_chapter_buttons(self) -> None:
        for child in self.chapter_list.winfo_children():
            child.destroy()
        self._chapter_rows.clear()
        if hasattr(self, "_book_rows"):
            self._book_rows.clear()

    def _on_sidebar_mode(self, value: str) -> None:
        self._sidebar_mode = value
        if hasattr(self, "chapter_search"):
            self.chapter_search.delete(0, "end")
        self._chapter_filter = ""
        self._refresh_sidebar_list()

    def _on_sidebar_search(self, _event=None) -> None:
        self._chapter_filter = self.chapter_search.get().strip()
        self._refresh_sidebar_list()

    def _sidebar_action(self) -> None:
        if self._sidebar_mode == "书架":
            self._scroll_to_current_book()
        else:
            self._scroll_to_current_chapter()

    def _refresh_sidebar_list(self) -> None:
        if not hasattr(self, "chapter_list"):
            return
        if self._sidebar_mode == "书架":
            if hasattr(self, "sidebar_section_label"):
                self.sidebar_section_label.configure(text="书架")
            if hasattr(self, "btn_sidebar_action"):
                self.btn_sidebar_action.configure(text="当前")
            self._fill_books()
        else:
            if hasattr(self, "sidebar_section_label"):
                self.sidebar_section_label.configure(text="目录")
            if hasattr(self, "btn_sidebar_action"):
                self.btn_sidebar_action.configure(text="定位")
            self._fill_chapters()

    def _show_catalog_placeholder(self) -> None:
        self._clear_chapter_buttons()
        self.catalog_count_label.configure(text="未加载")
        tip = ctk.CTkLabel(
            self.chapter_list,
            text="先导入小说到书架\n再点「目录」查看章节\n点击章节即可跳转",
            text_color=self.theme["faint"],
            font=self.font_ui,
            justify="left",
            anchor="w",
        )
        tip.pack(fill="x", padx=12, pady=20)

    def _show_bookshelf_placeholder(self) -> None:
        self._clear_chapter_buttons()
        self.catalog_count_label.configure(text="0 本")
        tip = ctk.CTkLabel(
            self.chapter_list,
            text="书架还是空的\n点击上方「导入小说」\n可一次选择多本",
            text_color=self.theme["faint"],
            font=self.font_ui,
            justify="left",
            anchor="w",
        )
        tip.pack(fill="x", padx=12, pady=20)

    def _on_chapter_search(self, _event=None) -> None:
        self._on_sidebar_search(_event)

    def _chapter_matches_filter(self, index: int, title: str) -> bool:
        q = self._chapter_filter.strip().lower()
        if not q:
            return True
        if q.isdigit() and int(q) == index + 1:
            return True
        return q in title.lower() or q in str(index + 1)

    def _book_matches_filter(self, book: dict) -> bool:
        q = self._chapter_filter.strip().lower()
        if not q:
            return True
        title = str(book.get("title") or "").lower()
        path = str(book.get("path") or "").lower()
        return q in title or q in path or q in Path(path).name.lower()

    def _fill_books(self) -> None:
        self._clear_chapter_buttons()
        books = list(self.library.get("books") or [])
        books.sort(key=lambda b: float(b.get("added_at") or 0), reverse=True)
        if not books:
            self._show_bookshelf_placeholder()
            return

        visible = 0
        for book in books:
            if not self._book_matches_filter(book):
                continue
            visible += 1
            self._add_book_row(book)

        total = len(books)
        if self._chapter_filter:
            self.catalog_count_label.configure(text=f"显示 {visible}/{total} 本")
        else:
            self.catalog_count_label.configure(text=f"共 {total} 本")

        if visible == 0:
            ctk.CTkLabel(
                self.chapter_list,
                text="没有匹配的书\n请换个关键词试试",
                text_color=self.theme["muted"],
                justify="left",
            ).pack(fill="x", padx=10, pady=16)
        else:
            self.after(60, self._scroll_to_current_book)

    def _add_book_row(self, book: dict) -> None:
        bid = str(book.get("id") or "")
        path = Path(str(book.get("path") or ""))
        title = str(book.get("title") or novel_display_title(path))
        is_current = bid == self.current_book_id
        exists = path.exists()
        bg = self.theme["accent_dim"] if is_current else self.theme["panel_soft"]
        hover = self.theme["chip"] if is_current else self.theme["chip_hover"]

        row = ctk.CTkFrame(self.chapter_list, fg_color=bg, corner_radius=10, cursor="hand2")
        row.pack(fill="x", padx=6, pady=3)
        row.grid_columnconfigure(0, weight=1)
        self._book_rows[bid] = row

        mark = "正在听 · " if is_current else ("" if exists else "缺失 · ")
        title_lbl = ctk.CTkLabel(
            row,
            text=f"{mark}{title}",
            anchor="w",
            justify="left",
            wraplength=210,
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=13, weight="bold" if is_current else "normal"),
            text_color=self.theme["accent"]
            if is_current
            else (self.theme["faint"] if not exists else self.theme["text"]),
        )
        title_lbl.grid(row=0, column=0, sticky="ew", padx=(10, 4), pady=(8, 0))

        chapters = int(book.get("chapter_count") or 0)
        chars = int(book.get("char_count") or 0)
        meta_bits = []
        if chapters:
            meta_bits.append(f"{chapters} 章")
        if chars:
            meta_bits.append(format_count(chars))
        meta_bits.append(path.suffix.lower().lstrip(".") or "文件")
        meta = ctk.CTkLabel(
            row,
            text=" · ".join(meta_bits),
            anchor="w",
            text_color=self.theme["accent"] if is_current else self.theme["faint"],
            font=self.font_small,
        )
        meta.grid(row=1, column=0, sticky="ew", padx=(10, 4), pady=(2, 8))

        ctk.CTkButton(
            row,
            text="×",
            width=28,
            height=28,
            corner_radius=6,
            fg_color=self.theme["chip"],
            hover_color=self.theme["stop"],
            text_color=self.theme["text"],
            font=self.font_small,
            command=lambda b=bid: self.remove_book(b),
        ).grid(row=0, column=1, rowspan=2, padx=(0, 8), pady=8)

        def bind_open(widget, book_id=bid):
            widget.bind("<Button-1>", lambda _e, i=book_id: self.open_book_by_id(i))
            widget.bind("<Enter>", lambda _e, r=row: r.configure(fg_color=hover))
            widget.bind(
                "<Leave>",
                lambda _e, r=row, cur=is_current: r.configure(
                    fg_color=self.theme["accent_dim"] if cur else self.theme["panel_soft"]
                ),
            )

        for w in (row, title_lbl, meta):
            bind_open(w)

    def _scroll_to_current_book(self) -> None:
        if not self.current_book_id:
            return
        row = self._book_rows.get(self.current_book_id)
        if not row:
            return
        try:
            self.chapter_list._parent_canvas.yview_moveto(0)
            self.update_idletasks()
            y = row.winfo_y()
            total = max(self.chapter_list._parent_canvas.bbox("all")[3], 1)
            self.chapter_list._parent_canvas.yview_moveto(max(0, (y - 40) / total))
        except Exception:
            pass

    def _fill_chapters(self) -> None:
        self._clear_chapter_buttons()
        total = len(self.chapters)
        if total == 0:
            self._show_catalog_placeholder()
            return

        visible = 0
        for idx, (title, body) in enumerate(self.chapters):
            if not self._chapter_matches_filter(idx, title):
                continue
            visible += 1
            self._add_chapter_row(idx, title, body)

        if self._chapter_filter:
            self.catalog_count_label.configure(text=f"显示 {visible}/{total} 章")
        else:
            self.catalog_count_label.configure(text=f"共 {total} 章")

        if visible == 0:
            ctk.CTkLabel(
                self.chapter_list,
                text="没有匹配的章节\n请换个关键词试试",
                text_color=self.theme["muted"],
                justify="left",
            ).pack(fill="x", padx=10, pady=16)
        else:
            self.after(60, self._scroll_to_current_chapter)

    def _add_chapter_row(self, idx: int, title: str, body: str) -> None:
        is_current = idx == self.chapter_index
        bg = self.theme["accent_dim"] if is_current else self.theme["panel_soft"]
        hover = self.theme["chip"] if is_current else self.theme["chip_hover"]
        accent = self.theme["accent"] if is_current else self.theme["chip"]

        row = ctk.CTkFrame(self.chapter_list, fg_color=bg, corner_radius=10, cursor="hand2")
        row.pack(fill="x", padx=6, pady=3)
        row.grid_columnconfigure(1, weight=1)
        self._chapter_rows[idx] = row

        num = ctk.CTkLabel(
            row,
            text=f"{idx + 1:02d}" if idx + 1 < 100 else str(idx + 1),
            width=40,
            height=40,
            corner_radius=8,
            fg_color=accent,
            text_color=self.theme["on_accent"] if is_current else self.theme["muted"],
            font=ctk.CTkFont(family="Microsoft YaHei UI", size=12, weight="bold"),
        )
        num.grid(row=0, column=0, rowspan=2, padx=(8, 8), pady=8, sticky="ns")

        mark = "正在听 · " if is_current else ""
        title_lbl = ctk.CTkLabel(
            row,
            text=f"{mark}{title}",
            anchor="w",
            justify="left",
            wraplength=200,
            font=ctk.CTkFont(
                family="Microsoft YaHei UI",
                size=13,
                weight="bold" if is_current else "normal",
            ),
            text_color=self.theme["accent"] if is_current else self.theme["text"],
        )
        title_lbl.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(8, 0))

        meta = ctk.CTkLabel(
            row,
            text=format_count(len(body)),
            anchor="w",
            text_color=self.theme["accent"] if is_current else self.theme["faint"],
            font=self.font_small,
        )
        meta.grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=(2, 8))

        def bind_click(widget, i=idx):
            widget.bind("<Button-1>", lambda _e, chapter=i: self.load_chapter(chapter, autoplay=False))
            widget.bind("<Enter>", lambda _e, r=row: r.configure(fg_color=hover))
            widget.bind(
                "<Leave>",
                lambda _e, r=row, cur=is_current: r.configure(
                    fg_color=self.theme["accent_dim"] if cur else self.theme["panel_soft"]
                ),
            )

        for w in (row, num, title_lbl, meta):
            bind_click(w)

    def _scroll_to_current_chapter(self) -> None:
        row = self._chapter_rows.get(self.chapter_index)
        if not row:
            return
        try:
            self.chapter_list._parent_canvas.yview_moveto(0)  # type: ignore[attr-defined]
            self.update_idletasks()
            y = row.winfo_y()
            total = max(self.chapter_list._parent_canvas.bbox("all")[3], 1)  # type: ignore[attr-defined]
            self.chapter_list._parent_canvas.yview_moveto(max(0, (y - 40) / total))  # type: ignore[attr-defined]
        except Exception:
            pass

    def _refresh_chapter_highlight(self) -> None:
        """切换章节后刷新目录高亮；在书架模式下不打断列表。"""
        if getattr(self, "_sidebar_mode", "目录") != "目录":
            return
        self._fill_chapters()

    def _library_books(self) -> list[dict]:
        books = self.library.get("books")
        return books if isinstance(books, list) else []

    def _find_book(self, book_id: str | None = None, path: Path | None = None) -> dict | None:
        if book_id:
            for b in self._library_books():
                if b.get("id") == book_id:
                    return b
        if path is not None:
            try:
                target = str(path.resolve())
            except Exception:
                target = str(path)
            for b in self._library_books():
                try:
                    if str(Path(b.get("path", "")).resolve()) == target:
                        return b
                except Exception:
                    if str(b.get("path")) == str(path):
                        return b
        return None

    def _persist_library(self) -> None:
        self.library["current_id"] = self.current_book_id
        save_library(self.library)

    def add_paths_to_library(self, paths: list[Path], switch_to_first: bool = True) -> list[Path]:
        """把文件加入书架，返回实际新增的路径。"""
        added: list[Path] = []
        first_pick: Path | None = None
        for raw in paths:
            path = Path(raw)
            if not is_novel_file(path):
                continue
            try:
                path = path.resolve()
            except Exception:
                pass
            existing = self._find_book(path=path)
            if existing:
                if first_pick is None:
                    first_pick = path
                continue
            book = {
                "id": book_id_for_path(path),
                "path": str(path),
                "title": novel_display_title(path),
                "added_at": time.time(),
                "chapter_count": 0,
                "char_count": 0,
            }
            self.library.setdefault("books", []).append(book)
            added.append(path)
            if first_pick is None:
                first_pick = path

        if added or first_pick:
            self._persist_library()

        if switch_to_first and first_pick is not None:
            if self.file_path is None or added:
                progress = load_json(PROGRESS_FILE, {})
                try:
                    key = str(first_pick.resolve())
                except Exception:
                    key = str(first_pick)
                restore = progress.get(key, {})
                self.load_novel(first_pick, restore=restore if isinstance(restore, dict) else None)
        elif self._sidebar_mode == "书架":
            self._fill_books()
        return added

    def update_book_meta(self, path: Path, chapters: int, chars: int) -> None:
        book = self._find_book(path=path)
        if not book:
            return
        book["chapter_count"] = chapters
        book["char_count"] = chars
        book["title"] = novel_display_title(path)
        self._persist_library()

    def remove_book(self, book_id: str) -> None:
        book = self._find_book(book_id=book_id)
        if not book:
            return
        title = book.get("title") or "这本小说"
        if not messagebox.askyesno(APP_NAME, f"从书架移除《{title}》？\n（不会删除磁盘文件）"):
            return
        self.library["books"] = [b for b in self._library_books() if b.get("id") != book_id]
        was_current = self.current_book_id == book_id
        if was_current:
            self.current_book_id = None
            self.file_path = None
            self.chapters = []
            self.sentences = []
            self.sentence_index = 0
            self.stop_play()
            self.title_label.configure(text="打开一本小说，开始收听")
            self.file_label.configure(text="支持 txt / pdf / doc / docx / epub 等")
            self._set_reader_text("已从书架移除。可继续导入其他小说。")
            self._setup_progress_slider()
            self._update_progress_ui(0)
        self._persist_library()
        self._refresh_sidebar_list()
        if was_current:
            remaining = self._library_books()
            if remaining:
                nxt = Path(remaining[0]["path"])
                progress = load_json(PROGRESS_FILE, {})
                try:
                    key = str(nxt.resolve())
                except Exception:
                    key = str(nxt)
                restore = progress.get(key)
                self.load_novel(nxt, restore=restore if isinstance(restore, dict) else None)

    def open_book_by_id(self, book_id: str) -> None:
        book = self._find_book(book_id=book_id)
        if not book:
            return
        path = Path(str(book.get("path") or ""))
        if not path.exists():
            messagebox.showerror(APP_NAME, f"文件不存在或已移动：\n{path}\n可从书架移除后重新导入。")
            return
        if self.current_book_id == book_id and self.chapters:
            self._sidebar_mode = "目录"
            if hasattr(self, "sidebar_mode"):
                self.sidebar_mode.set("目录")
            self._refresh_sidebar_list()
            return
        self._save_progress()
        progress = load_json(PROGRESS_FILE, {})
        try:
            key = str(path.resolve())
        except Exception:
            key = str(path)
        restore = progress.get(key, {})
        self.load_novel(path, restore=restore if isinstance(restore, dict) else None)

    def import_novels(self) -> None:
        paths = filedialog.askopenfilenames(
            title="选择一本或多本小说",
            filetypes=NOVEL_FILETYPES,
        )
        if not paths:
            return
        added = self.add_paths_to_library([Path(p) for p in paths], switch_to_first=True)
        self._sidebar_mode = "书架"
        if hasattr(self, "sidebar_mode"):
            self.sidebar_mode.set("书架")
        self._refresh_sidebar_list()
        if added:
            self._ui_status(f"已导入 {len(added)} 本到书架")
        else:
            self._ui_status("所选文件已在书架中")

    def import_folder(self) -> None:
        folder = filedialog.askdirectory(title="选择包含小说的文件夹")
        if not folder:
            return
        root = Path(folder)
        found: list[Path] = []
        for p in root.rglob("*"):
            if is_novel_file(p):
                found.append(p)
            if len(found) >= 300:
                break
        if not found:
            messagebox.showinfo(APP_NAME, "该文件夹下没有找到可识别的小说文件。")
            return
        if len(found) > 80:
            if not messagebox.askyesno(APP_NAME, f"找到 {len(found)} 个文件，是否全部加入书架？"):
                return
        added = self.add_paths_to_library(found, switch_to_first=True)
        self._sidebar_mode = "书架"
        if hasattr(self, "sidebar_mode"):
            self.sidebar_mode.set("书架")
        self._refresh_sidebar_list()
        self._ui_status(f"文件夹导入完成 · 新增 {len(added)} 本 · 合计扫描 {len(found)} 个")

    def open_file(self) -> None:
        self.import_novels()

    def load_novel(self, path: Path, restore: dict | None = None) -> None:
        try:
            text = read_document(path)
        except Exception as exc:
            messagebox.showerror(APP_NAME, f"无法读取文件:\n{exc}")
            return

        if len(text) > 3_000_000:
            if not messagebox.askyesno(
                APP_NAME,
                f"文件较大（约 {len(text) // 10000} 万字），加载可能稍慢，是否继续？",
            ):
                return

        self.stop_play()
        try:
            path = path.resolve()
        except Exception:
            pass

        # 加入书架（不递归切换）
        if not self._find_book(path=path):
            self.library.setdefault("books", []).append(
                {
                    "id": book_id_for_path(path),
                    "path": str(path),
                    "title": novel_display_title(path),
                    "added_at": time.time(),
                    "chapter_count": 0,
                    "char_count": 0,
                }
            )
        book = self._find_book(path=path)
        self.current_book_id = book["id"] if book else book_id_for_path(path)
        self._persist_library()

        self.file_path = path
        self.chapters = split_chapters(text)
        self.chapter_index = 0
        self.content_matches = []
        self.content_match_index = -1
        self._content_query = ""
        if hasattr(self, "chapter_search") and self._sidebar_mode == "目录":
            self.chapter_search.delete(0, "end")
            self._chapter_filter = ""
        if hasattr(self, "content_search_entry"):
            self.content_search_entry.delete(0, "end")
            self.content_match_label.configure(text="")
        self.file_label.configure(text=path.name)
        self.update_book_meta(path, chapters=len(self.chapters), chars=len(text))

        chapter_index = 0
        sentence_index = 0
        if restore:
            chapter_index = min(int(restore.get("chapter_index", 0)), max(0, len(self.chapters) - 1))
            sentence_index = int(restore.get("sentence_index", 0))

        self._sidebar_mode = "目录"
        if hasattr(self, "sidebar_mode"):
            self.sidebar_mode.set("目录")

        self.load_chapter(chapter_index, sentence_index=sentence_index, autoplay=False)
        self._refresh_sidebar_list()
        self._ui_status(f"正在听《{novel_display_title(path)}》· 共 {len(self.chapters)} 章")

    def load_chapter(
        self,
        index: int,
        sentence_index: int = 0,
        autoplay: bool = False,
        keep_search_highlight: bool = False,
    ) -> None:
        if not self.chapters:
            return
        self.stop_play()
        self.chapter_index = max(0, min(index, len(self.chapters) - 1))
        title, body = self.chapters[self.chapter_index]
        self.sentences = split_sentences(body)
        self.sentence_index = max(0, min(sentence_index, max(0, len(self.sentences) - 1)))
        self._sentence_spans = build_sentence_spans(body, self.sentences)

        self.title_label.configure(text=f"第 {self.chapter_index + 1} / {len(self.chapters)} 章 · {title}")
        self._set_reader_text(body)
        self._refresh_chapter_highlight()
        self._setup_progress_slider()
        self._update_progress_ui(self.sentence_index)
        if self.sentences:
            self._highlight_by_sentence_index(self.sentence_index, scroll=True)
        self._save_progress()
        self._refresh_mini()

        if keep_search_highlight and self._content_query:
            self._highlight_all_query_in_current_chapter()
        if autoplay and self.sentences:
            self.start_play(from_index=self.sentence_index)

    def _on_search_scope(self, value: str) -> None:
        self._search_scope = value
        if self.content_search_entry.get().strip():
            self.search_content()

    def search_content(self) -> None:
        if not self.chapters:
            messagebox.showinfo(APP_NAME, "请先打开一本小说。")
            return
        query = self.content_search_entry.get().strip()
        if not query:
            messagebox.showinfo(APP_NAME, "请输入要搜索的正文关键词。")
            return

        self._content_query = query
        self.content_matches = []
        scope = self.search_scope.get() if hasattr(self, "search_scope") else "全书"
        self._search_scope = scope

        chapter_indexes = (
            [self.chapter_index]
            if scope == "本章"
            else list(range(len(self.chapters)))
        )

        for ci in chapter_indexes:
            _title, body = self.chapters[ci]
            for offset in find_all_offsets(body, query):
                sent_i = offset_to_sentence_index(body, offset)
                snippet = make_snippet(body, offset, len(query))
                self.content_matches.append((ci, offset, sent_i, snippet))

        if not self.content_matches:
            self.content_match_index = -1
            self.content_match_label.configure(text="无结果")
            self._ui_status(f"未找到「{query}」")
            messagebox.showinfo(APP_NAME, f"在{scope}范围内未找到：{query}")
            return

        # 优先定位到当前章内第一条匹配，否则全书第一条
        start_at = 0
        for i, (ci, _, _, _) in enumerate(self.content_matches):
            if ci == self.chapter_index:
                start_at = i
                break

        self.content_match_index = start_at
        self._apply_content_match(self.content_match_index)
        self._ui_status(f"找到 {len(self.content_matches)} 处「{query}」")

    def goto_content_match(self, step: int) -> None:
        if not self.content_matches:
            self.search_content()
            return
        if not self.content_matches:
            return
        self.content_match_index = (self.content_match_index + step) % len(self.content_matches)
        self._apply_content_match(self.content_match_index)

    def play_from_match(self) -> None:
        if not self.content_matches:
            self.search_content()
            if not self.content_matches:
                return
        if self.content_match_index < 0:
            self.content_match_index = 0
        chapter_i, _offset, sent_i, _snip = self.content_matches[self.content_match_index]
        if chapter_i != self.chapter_index:
            self.load_chapter(chapter_i, sentence_index=sent_i, keep_search_highlight=True)
        else:
            self.sentence_index = sent_i
            self._highlight_all_query_in_current_chapter()
            self._focus_match_offset(_offset)
        self.start_play(from_index=sent_i)

    def _apply_content_match(self, match_index: int) -> None:
        if not self.content_matches:
            return
        match_index = max(0, min(match_index, len(self.content_matches) - 1))
        self.content_match_index = match_index
        chapter_i, offset, sent_i, snippet = self.content_matches[match_index]
        total = len(self.content_matches)
        self.content_match_label.configure(text=f"{match_index + 1}/{total}")

        if chapter_i != self.chapter_index:
            self.load_chapter(chapter_i, sentence_index=sent_i, keep_search_highlight=True)
        else:
            self.sentence_index = sent_i
            self._highlight_all_query_in_current_chapter()

        self._focus_match_offset(offset)
        title = self.chapters[chapter_i][0]
        self._ui_status(f"定位 {match_index + 1}/{total} · 第{chapter_i + 1}章 · {snippet}")

    def _highlight_all_query_in_current_chapter(self) -> None:
        query = self._content_query
        if not query or not self.chapters:
            return
        body = self.chapters[self.chapter_index][1]
        tb = self._reader_tb()
        tb.configure(state="normal")
        tb.tag_remove("search_hit", "1.0", "end")
        tb.tag_remove("search_current", "1.0", "end")
        tb.tag_config("search_hit", background=self.theme["hit"], foreground=self.theme["hit_fg"])
        tb.tag_config("search_current", background=self.theme["hit_cur"], foreground=self.theme["hit_cur_fg"])

        for offset in find_all_offsets(body, query):
            start = self._index_at_offset(offset)
            end = self._index_at_offset(offset + len(query))
            tb.tag_add("search_hit", start, end)

    def _focus_match_offset(self, offset: int) -> None:
        query = self._content_query
        if not query:
            return
        tb = self._reader_tb()
        tb.configure(state="normal")
        tb.tag_remove("search_current", "1.0", "end")
        start = self._index_at_offset(offset)
        end = self._index_at_offset(offset + len(query))
        tb.tag_add("search_current", start, end)
        tb.tag_config("search_current", background=self.theme["hit_cur"], foreground=self.theme["hit_cur_fg"])
        self._scroll_reader_to(start)
        self._save_progress()

    def start_play(self, from_index: int | None = None) -> None:
        if not self.sentences:
            messagebox.showinfo(APP_NAME, "当前章节没有可朗读的内容。")
            return
        idx = self.sentence_index if from_index is None else from_index
        self.playing = True
        self.paused = False
        self._sync_transport_ui()
        self.player.configure(self.speed_value, self.voice_id, self.volume_value)
        self.player.play(self.sentences, idx)

    def toggle_play(self) -> None:
        if not self.chapters:
            if self._mini_mode:
                self.exit_mini_mode()
            self.open_file()
            return
        if not self.playing:
            self.start_play()
            return
        if self.paused:
            self.paused = False
            self.player.resume()
        else:
            self.paused = True
            self.player.pause()
        self._sync_transport_ui()

    def stop_play(self) -> None:
        self.player.stop()
        self.playing = False
        self.paused = False
        self._sync_transport_ui()

    def _sync_transport_ui(self) -> None:
        if hasattr(self, "btn_play"):
            if self.playing and not self.paused:
                self.btn_play.configure(text="⏸  暂停")
            elif self.playing and self.paused:
                self.btn_play.configure(text="▶  继续")
            else:
                self.btn_play.configure(text="▶  播放")
        self._refresh_mini()

    def _nudge_volume(self, delta: float) -> None:
        self.volume_value = max(0.0, min(1.0, round(self.volume_value + delta, 2)))
        if hasattr(self, "vol_slider"):
            self.vol_slider.set(self.volume_value)
        if hasattr(self, "vol_label"):
            self.vol_label.configure(text=f"{int(self.volume_value * 100)}%")
        self.player.configure(self.speed_value, self.voice_id, self.volume_value)
        self._save_settings_only()
        self._ui_status(f"音量 {int(self.volume_value * 100)}%")

    def _start_hotkeys(self) -> None:
        ok = self.hotkeys.start(self.hotkey_bindings)
        self.after(80, self._poll_hotkeys)
        if ok:
            self._ui_status(hotkeys_help_text(self.hotkey_bindings))
        else:
            self._ui_status("全局快捷键注册失败（可能被其他程序占用）")

    def open_hotkey_settings(self) -> None:
        if self._hotkey_win is not None:
            try:
                if self._hotkey_win.winfo_exists():
                    self._hotkey_win.lift()
                    self._hotkey_win.focus_force()
                    return
            except Exception:
                pass
        self._hotkey_win = HotkeySettingsWindow(self)

    def apply_hotkey_bindings(self, bindings: dict[str, str]) -> None:
        self.hotkey_bindings = merge_hotkeys(bindings)
        self._save_settings_only()
        ok = self.hotkeys.start(self.hotkey_bindings)
        if hasattr(self, "hotkey_tip"):
            self.hotkey_tip.configure(text=hotkeys_help_text(self.hotkey_bindings))
        if ok:
            self._ui_status("快捷键已更新并生效")
        else:
            self._ui_status("快捷键保存了，但注册失败（可能被占用）")

    def _poll_hotkeys(self) -> None:
        for action in self.hotkeys.poll():
            self._dispatch_hotkey(action)
        self.after(80, self._poll_hotkeys)

    def _dispatch_hotkey(self, action: str) -> None:
        if action == "toggle_play":
            self.toggle_play()
        elif action == "stop":
            self.stop_play()
            self._ui_status("已停止")
        elif action == "prev_chapter":
            self.prev_chapter()
        elif action == "next_chapter":
            self.next_chapter()
        elif action == "volume_up":
            self._nudge_volume(0.1)
        elif action == "volume_down":
            self._nudge_volume(-0.1)
        elif action == "speed_up":
            self._nudge_speed(0.1)
        elif action == "speed_down":
            self._nudge_speed(-0.1)
        elif action == "toggle_mini":
            self.toggle_mini_mode()

    def toggle_mini_mode(self) -> None:
        if self._mini_mode:
            self.exit_mini_mode()
        else:
            self.enter_mini_mode()

    def enter_mini_mode(self) -> None:
        if self._mini_mode and self.mini and self.mini.winfo_exists():
            try:
                self.mini.lift()
                self.mini.focus_force()
            except Exception:
                pass
            return
        self._mini_mode = True
        self.withdraw()
        if self.mini is None or not self.mini.winfo_exists():
            self.mini = MiniControlWindow(self)
        else:
            self.mini.deiconify()
            self.mini.lift()
        self._refresh_mini()
        self._ui_status("已进入小窗模式（Ctrl+Alt+M 可切换）")

    def exit_mini_mode(self) -> None:
        self._mini_mode = False
        if self.mini is not None:
            try:
                if self.mini.winfo_exists():
                    self.mini.destroy()
            except Exception:
                pass
            self.mini = None
        self.deiconify()
        self.lift()
        try:
            self.focus_force()
        except Exception:
            pass

    def _refresh_mini(self) -> None:
        if self.mini is not None:
            try:
                if self.mini.winfo_exists():
                    self.mini.refresh()
            except Exception:
                pass

    def prev_chapter(self) -> None:
        if not self.chapters:
            return
        self.load_chapter(self.chapter_index - 1, autoplay=self.playing and not self.paused)

    def next_chapter(self) -> None:
        if not self.chapters:
            return
        if self.chapter_index >= len(self.chapters) - 1:
            self._ui_status("已经是最后一章")
            return
        self.load_chapter(self.chapter_index + 1, autoplay=self.playing and not self.paused)

    def _on_volume(self, value) -> None:
        self.volume_value = float(value)
        self.vol_label.configure(text=f"{int(self.volume_value * 100)}%")
        self.player.configure(self.speed_value, self.voice_id, self.volume_value)
        self._save_settings_only()

    def _on_voice(self, name: str) -> None:
        for vid, vname in self.voices:
            if vname == name:
                self.voice_id = vid
                break
        self.player.configure(self.speed_value, self.voice_id, self.volume_value)
        self._save_settings_only()
        if self.playing:
            self._ui_status("讲书音色已切换（下一段生效，更接近真人播讲）")
        else:
            self._ui_status("已选择真人讲书音色")

    def _ui_status(self, text: str) -> None:
        # 播放线程只投递队列，由主线程轮询更新（tk 非线程安全）
        self._play_ui_q.put(("status", text))

    def _ui_sentence(self, start_i: int, end_i: int, sentence: str) -> None:
        self._play_ui_q.put(("sentence", start_i, end_i, sentence))

    def _ui_finished(self) -> None:
        self._play_ui_q.put(("finished",))

    def _drain_play_ui(self) -> None:
        latest_sentence = None
        latest_status = None
        finished = False
        while True:
            try:
                item = self._play_ui_q.get_nowait()
            except queue.Empty:
                break
            kind = item[0]
            if kind == "status":
                latest_status = item[1]
            elif kind == "sentence":
                latest_sentence = item
            elif kind == "finished":
                finished = True
        try:
            if latest_status is not None and hasattr(self, "status_label"):
                self.status_label.configure(text=latest_status)
                self._refresh_mini()
            if latest_sentence is not None:
                _k, start_i, end_i, _sentence = latest_sentence
                self._apply_sentence_progress(start_i, end_i)
            if finished:
                self._apply_finished()
        except Exception:
            pass
        self.after(40, self._drain_play_ui)

    def _apply_sentence_progress(self, start_i: int, end_i: int) -> None:
        if not self.sentences:
            return
        start_i = max(0, min(start_i, len(self.sentences) - 1))
        end_i = max(start_i, min(end_i, len(self.sentences) - 1))
        self.sentence_index = start_i
        total = len(self.sentences)
        if start_i == end_i:
            tip = f"句 {start_i + 1}/{total}"
        else:
            tip = f"句 {start_i + 1}-{end_i + 1}/{total}"
        if hasattr(self, "status_label"):
            self.status_label.configure(
                text=f"朗读中 · {speed_label(self.speed_value)} · {tip}"
            )
        self._highlight_range(start_i, end_i, scroll=True)
        if not self._progress_dragging:
            self._update_progress_ui(start_i)
        self._refresh_mini()
        if start_i % 3 == 0:
            self._save_progress()

    def _apply_finished(self) -> None:
        self.playing = False
        self.paused = False
        self._sync_transport_ui()
        if self.chapter_index < len(self.chapters) - 1:
            if hasattr(self, "status_label"):
                self.status_label.configure(text="本章结束，自动下一章…")
            self._refresh_mini()
            self.after(400, lambda: self.load_chapter(self.chapter_index + 1, autoplay=True))
        else:
            if hasattr(self, "status_label"):
                self.status_label.configure(text="全书朗读完成")
            self._refresh_mini()
            self._save_progress()

    def _setup_progress_slider(self) -> None:
        if not hasattr(self, "progress_slider"):
            return
        total = max(1, len(self.sentences))
        steps = max(1, total - 1)
        self._suppress_progress_event = True
        try:
            self.progress_slider.configure(from_=0, to=max(0, total - 1), number_of_steps=steps)
            self.progress_slider.set(min(self.sentence_index, max(0, total - 1)))
        finally:
            self._suppress_progress_event = False

    def _update_progress_ui(self, index: int) -> None:
        if not hasattr(self, "progress_slider"):
            return
        total = len(self.sentences)
        if total <= 0:
            self.progress_label.configure(text="进度 —")
            self.progress_pct_label.configure(text="0%")
            return
        index = max(0, min(index, total - 1))
        pct = int(round((index + 1) / total * 100))
        self.progress_label.configure(text=f"句 {index + 1}/{total}")
        self.progress_pct_label.configure(text=f"{pct}%")
        self._suppress_progress_event = True
        try:
            self.progress_slider.set(index)
        finally:
            self._suppress_progress_event = False

    def _bind_progress_slider_release(self) -> None:
        def mark_drag(_e=None):
            self._progress_dragging = True

        def on_release(_e=None):
            self._progress_dragging = False
            self._commit_progress_seek()

        widgets = [self.progress_slider]
        try:
            widgets.extend(self.progress_slider.winfo_children())
        except Exception:
            pass
        for w in widgets:
            try:
                w.bind("<ButtonPress-1>", mark_drag, add="+")
                w.bind("<ButtonRelease-1>", on_release, add="+")
            except Exception:
                pass

    def _on_progress_drag(self, value) -> None:
        if self._suppress_progress_event:
            return
        if not self.sentences:
            return
        self._progress_dragging = True
        idx = int(round(float(value)))
        idx = max(0, min(idx, len(self.sentences) - 1))
        total = len(self.sentences)
        pct = int(round((idx + 1) / total * 100))
        self.progress_label.configure(text=f"句 {idx + 1}/{total}")
        self.progress_pct_label.configure(text=f"{pct}%")
        self._highlight_by_sentence_index(idx, scroll=True)
        if self._progress_seek_job is not None:
            try:
                self.after_cancel(self._progress_seek_job)
            except Exception:
                pass
        self._progress_seek_job = self.after(320, self._commit_progress_seek)

    def _commit_progress_seek(self) -> None:
        self._progress_seek_job = None
        self._progress_dragging = False
        if not self.sentences:
            return
        idx = int(round(float(self.progress_slider.get())))
        idx = max(0, min(idx, len(self.sentences) - 1))
        was_playing = self.playing and not self.paused
        self.sentence_index = idx
        self._highlight_by_sentence_index(idx, scroll=True)
        self._update_progress_ui(idx)
        self._save_progress()
        if was_playing:
            self.start_play(from_index=idx)
        else:
            self._ui_status(f"已定位到句 {idx + 1}/{len(self.sentences)} · 点播放或继续拖动")

    def _char_offset_at_click(self, event) -> int | None:
        try:
            tb = self.text_box._textbox
            index = tb.index(f"@{event.x},{event.y}")
            # 字符数：从开头到点击处（不含点击后）
            return len(tb.get("1.0", index))
        except Exception:
            return None

    def _sentence_index_from_offset(self, offset: int) -> int:
        if not self._sentence_spans:
            if self.chapters:
                return offset_to_sentence_index(self.chapters[self.chapter_index][1], offset)
            return 0
        for i, (start, end) in enumerate(self._sentence_spans):
            if start <= offset < end:
                return i
            if offset < start:
                return max(0, i - 1)
        return max(0, len(self._sentence_spans) - 1)

    def _on_reader_click(self, event):
        if not self.chapters or not self.sentences:
            return
        offset = self._char_offset_at_click(event)
        if offset is None:
            return
        if self._reader_click_job is not None:
            try:
                self.after_cancel(self._reader_click_job)
            except Exception:
                pass
        # 延迟一点，若随后是双击则取消单击定位
        self._reader_click_job = self.after(
            220, lambda o=offset: self._locate_from_offset(o, autoplay=False)
        )

    def _on_reader_double_click(self, event):
        if not self.chapters or not self.sentences:
            return
        if self._reader_click_job is not None:
            try:
                self.after_cancel(self._reader_click_job)
            except Exception:
                pass
            self._reader_click_job = None
        offset = self._char_offset_at_click(event)
        if offset is None:
            return
        self._locate_from_offset(offset, autoplay=True)
        return "break"

    def _locate_from_offset(self, offset: int, autoplay: bool) -> None:
        self._reader_click_job = None
        if not self.sentences:
            return
        idx = self._sentence_index_from_offset(offset)
        was_playing = self.playing and not self.paused
        self.sentence_index = idx
        self._highlight_by_sentence_index(idx, scroll=True)
        self._update_progress_ui(idx)
        self._save_progress()
        if autoplay or was_playing:
            self.start_play(from_index=idx)
            self._ui_status(f"从此处朗读 · 句 {idx + 1}/{len(self.sentences)}")
        else:
            self._ui_status(f"已定位 · 句 {idx + 1}/{len(self.sentences)} · 双击可立即播放")

    def _reader_tb(self):
        try:
            return self.text_box._textbox
        except Exception:
            return self.text_box

    def _block_reader_edit(self, event):
        if (event.state & 0x4) and event.keysym.lower() in ("c", "a"):
            return None
        return "break"

    def _setup_reader_readonly(self) -> None:
        """正文保持可打标签的 normal 状态，仅拦截编辑按键。"""
        tb = self._reader_tb()
        try:
            tb.configure(state="normal", exportselection=1)
            self.text_box.configure(state="normal")
        except Exception:
            pass
        for seq in ("<Key>", "<KeyPress>", "<<Paste>>", "<Button-2>"):
            try:
                tb.bind(seq, self._block_reader_edit, add="+")
            except Exception:
                pass
        self._ensure_reader_tags()

    def _ensure_reader_tags(self) -> None:
        tb = self._reader_tb()
        bg = self.theme.get("speak", "#1b7a4a")
        fg = self.theme.get("speak_fg", "#ffffff")
        line_bg = self.theme.get("accent_dim", "#1e3d2c")
        try:
            tb.tag_configure("current_line", background=line_bg)
            tb.tag_configure("current", background=bg, foreground=fg)
            tb.tag_raise("current_line")
            tb.tag_raise("current")
        except Exception:
            pass

    def _set_reader_text(self, body: str) -> None:
        tb = self._reader_tb()
        try:
            self.text_box.configure(state="normal")
            tb.configure(state="normal")
        except Exception:
            pass
        try:
            tb.delete("1.0", "end")
            tb.insert("1.0", body)
        except Exception:
            self.text_box.delete("1.0", "end")
            self.text_box.insert("1.0", body)
        self._ensure_reader_tags()

    def _index_at_offset(self, offset: int) -> str:
        tb = self._reader_tb()
        offset = max(0, int(offset))
        try:
            return tb.index(f"1.0+{offset}c")
        except Exception:
            return "1.0"

    def _highlight_by_sentence_index(self, index: int, scroll: bool = True) -> None:
        self._highlight_range(index, index, scroll=scroll)

    def _highlight_range(self, start_i: int, end_i: int, scroll: bool = True) -> None:
        if not self.sentences or not hasattr(self, "text_box"):
            return
        start_i = max(0, min(start_i, len(self.sentences) - 1))
        end_i = max(start_i, min(end_i, len(self.sentences) - 1))
        tb = self._reader_tb()
        try:
            tb.configure(state="normal")
            self.text_box.configure(state="normal")
        except Exception:
            pass
        self._ensure_reader_tags()
        tb.tag_remove("current", "1.0", "end")
        tb.tag_remove("current_line", "1.0", "end")

        start = end = None
        if (
            self._sentence_spans
            and start_i < len(self._sentence_spans)
            and end_i < len(self._sentence_spans)
        ):
            start_off, _ = self._sentence_spans[start_i]
            _, end_off = self._sentence_spans[end_i]
            if end_off > start_off:
                start = self._index_at_offset(start_off)
                end = self._index_at_offset(end_off)
                got = tb.get(start, end)
                expect = "".join(self.sentences[start_i : end_i + 1])
                if got[:20] != expect[:20]:
                    start = end = None

        if start is None or end is None:
            sent = self.sentences[start_i]
            needle = sent[:40] if len(sent) > 40 else sent
            from_idx = "1.0"
            if self._sentence_spans and start_i < len(self._sentence_spans):
                from_idx = self._index_at_offset(max(0, self._sentence_spans[start_i][0] - 4))
            start = tb.search(needle, from_idx, stopindex="end")
            if not start:
                start = tb.search(needle, "1.0", stopindex="end")
            if not start:
                return
            end = f"{start}+{min(len(sent), 240)}c"

        try:
            line_start = tb.index(f"{start} linestart")
            line_end = tb.index(f"{end} lineend +1c")
            tb.tag_add("current_line", line_start, line_end)
        except Exception:
            pass
        tb.tag_add("current", start, end)
        try:
            tb.tag_raise("current_line")
            tb.tag_raise("current")
        except Exception:
            pass
        if scroll:
            self._scroll_reader_to(start)

    def _scroll_reader_to(self, index: str) -> None:
        """强制把朗读位置滚到可视区中部。"""
        tb = self._reader_tb()
        try:
            tb.see(index)
            self.update_idletasks()
            total_lines = max(1, int(float(tb.index("end-1c").split(".")[0])))
            cur_line = max(1, int(float(tb.index(index).split(".")[0])))
            frac = (cur_line - 1) / total_lines
            top, bottom = tb.yview()
            view = max(0.12, bottom - top)
            target = max(0.0, min(1.0, frac - view * 0.35))
            tb.yview_moveto(target)
            tb.see(index)
        except Exception:
            try:
                self.text_box.see(index)
            except Exception:
                pass

    def _highlight_sentence(self, sentence: str) -> None:
        if not sentence or not self.sentences:
            return
        try:
            idx = self.sentences.index(sentence)
        except ValueError:
            idx = -1
        if idx >= 0:
            self._highlight_by_sentence_index(idx, scroll=True)

    def _on_theme_change(self, name: str) -> None:
        if name == self.theme_name or name not in THEMES:
            return
        self.apply_theme(name)

    def apply_theme(self, name: str) -> None:
        """切换主题并重建界面，保留当前小说与进度。"""
        if name not in THEMES:
            return
        was_playing = self.playing and not self.paused
        was_mini = self._mini_mode
        chapter_filter = self._chapter_filter
        content_query = self._content_query
        search_scope = self._search_scope
        match_index = self.content_match_index
        matches = list(self.content_matches)

        self.stop_play()
        if was_mini:
            self._mini_mode = False
            if self.mini is not None:
                try:
                    self.mini.destroy()
                except Exception:
                    pass
                self.mini = None
            self.deiconify()

        self.theme_name = name
        self.theme = THEMES[name]
        self._save_settings_only()

        ctk.set_appearance_mode(self.theme.get("mode", "dark"))
        self.configure(fg_color=self.theme["bg"])

        for child in self.winfo_children():
            child.destroy()
        self._chapter_rows.clear()
        if hasattr(self, "_book_rows"):
            self._book_rows.clear()

        self._build_ui()

        # 恢复小说内容
        if self.file_path:
            self.file_label.configure(text=self.file_path.name)
        if self.chapters:
            title, body = self.chapters[self.chapter_index]
            self.title_label.configure(
                text=f"第 {self.chapter_index + 1} / {len(self.chapters)} 章 · {title}"
            )
            if not self.sentences:
                self.sentences = split_sentences(body)
            self._sentence_spans = build_sentence_spans(body, self.sentences)
            self._set_reader_text(body)
            self._setup_progress_slider()
            self._update_progress_ui(self.sentence_index)
            if self.sentences:
                self._highlight_by_sentence_index(self.sentence_index, scroll=True)
            if chapter_filter:
                self.chapter_search.insert(0, chapter_filter)
                self._chapter_filter = chapter_filter
            self._fill_chapters()

        if content_query:
            self.content_search_entry.insert(0, content_query)
            self._content_query = content_query
            self.search_scope.set(search_scope)
            self._search_scope = search_scope
            self.content_matches = matches
            self.content_match_index = match_index
            if matches and 0 <= match_index < len(matches):
                self.content_match_label.configure(text=f"{match_index + 1}/{len(matches)}")
                self._highlight_all_query_in_current_chapter()
                _ci, offset, _si, _snip = matches[match_index]
                if _ci == self.chapter_index:
                    self._focus_match_offset(offset)

        play_text = "⏸  暂停" if was_playing else "▶  播放"
        self.btn_play.configure(text=play_text)
        self._ui_status(f"已切换主题：{name}")
        if was_playing and self.sentences:
            self.start_play(from_index=self.sentence_index)
        if was_mini:
            self.after(120, self.enter_mini_mode)

    def _save_settings_only(self) -> None:
        save_json(
            SETTINGS_FILE,
            {
                "speed": self.speed_value,
                "volume": self.volume_value,
                "voice_id": self.voice_id,
                "theme": self.theme_name,
                "hotkeys": self.hotkey_bindings,
            },
        )

    def _save_progress(self) -> None:
        self._save_settings_only()
        if not self.file_path:
            return
        data = load_json(PROGRESS_FILE, {})
        data[str(self.file_path.resolve())] = {
            "chapter_index": self.chapter_index,
            "sentence_index": self.sentence_index,
            "file_name": self.file_path.name,
        }
        data["_last"] = str(self.file_path.resolve())
        save_json(PROGRESS_FILE, data)

    def _try_restore_last(self) -> None:
        # 把历史进度里的书迁入书架
        progress = load_json(PROGRESS_FILE, {})
        migrated = False
        for key, meta in progress.items():
            if key.startswith("_") or not isinstance(meta, dict):
                continue
            p = Path(key)
            if p.exists() and not self._find_book(path=p):
                self.library.setdefault("books", []).append(
                    {
                        "id": book_id_for_path(p),
                        "path": str(p.resolve()),
                        "title": str(meta.get("file_name") or novel_display_title(p)),
                        "added_at": time.time(),
                        "chapter_count": 0,
                        "char_count": 0,
                    }
                )
                migrated = True
        if migrated:
            self._persist_library()
            if self._sidebar_mode == "书架":
                self._fill_books()

        last = None
        if self.current_book_id:
            book = self._find_book(book_id=self.current_book_id)
            if book:
                last = str(book.get("path") or "")
        if not last:
            last = progress.get("_last")
        if not last:
            books = self._library_books()
            if books:
                last = books[0].get("path")
        if not last:
            return
        path = Path(last)
        if not path.exists():
            return
        restore = progress.get(str(path.resolve()), progress.get(last, {}))
        tip = f"是否继续上次阅读？\n{path.name}"
        if messagebox.askyesno(APP_NAME, tip):
            self.load_novel(path, restore=restore if isinstance(restore, dict) else None)
        else:
            # 不继续也刷新书架显示
            self._sidebar_mode = "书架"
            if hasattr(self, "sidebar_mode"):
                self.sidebar_mode.set("书架")
            self._refresh_sidebar_list()

    def _on_close(self) -> None:
        self._save_progress()
        self.stop_play()
        try:
            self.hotkeys.stop()
        except Exception:
            pass
        if self.mini is not None:
            try:
                self.mini.destroy()
            except Exception:
                pass
            self.mini = None
        try:
            pygame.mixer.quit()
        except Exception:
            pass
        self.destroy()


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
