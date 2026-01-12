from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


DEFAULT_CHAPTER_SPLIT_RE = re.compile(r"^第[零一二三四五六七八九十百千0-9]+章.*$", re.M)
DEFAULT_MD_HEADING_RE = re.compile(r"^#\s+第.*章.*$", re.M)


@dataclass
class ImportResult:
    chapters: list[tuple[str, str]]  # (title, content)
    warnings: list[str]


def split_book_to_chapters(text: str) -> ImportResult:
    """
    Very small MVP splitter:
    - Prefer headings matching '第X章...'
    - Otherwise returns a single chapter.
    """
    warnings: list[str] = []
    lines = text.splitlines()

    # find split points by line matching
    split_indices: list[int] = []
    for i, line in enumerate(lines):
        if DEFAULT_CHAPTER_SPLIT_RE.match(line) or DEFAULT_MD_HEADING_RE.match(line):
            split_indices.append(i)

    if not split_indices:
        warnings.append("未检测到章节分隔符，已按单章导入。可在后续版本提供导入向导。")
        return ImportResult(chapters=[("第1章", text)], warnings=warnings)

    # build segments
    split_indices.append(len(lines))
    chapters: list[tuple[str, str]] = []
    for idx in range(len(split_indices) - 1):
        start = split_indices[idx]
        end = split_indices[idx + 1]
        title = lines[start].strip() or f"第{idx+1}章"
        content = "\n".join(lines[start + 1 : end]).lstrip("\n")
        chapters.append((title, content))

    return ImportResult(chapters=chapters, warnings=warnings)


def export_chapters_to_markdown(chapters: list[tuple[str, str]], include_toc: bool = True) -> str:
    parts: list[str] = []
    if include_toc:
        parts.append("# 目录\n")
        for i, (title, _) in enumerate(chapters, start=1):
            parts.append(f"- {i}. {title}")
        parts.append("\n---\n")

    for title, content in chapters:
        parts.append(f"# {title}\n")
        parts.append(content.rstrip() + "\n")
        parts.append("\n---\n")

    return "\n".join(parts).rstrip() + "\n"


def read_text_file(path: Path) -> str:
    # MVP: assume UTF-8; later add encoding detection.
    return path.read_text(encoding="utf-8")

