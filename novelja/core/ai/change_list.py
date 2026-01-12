from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


ChangeKind = Literal["replace", "insert_before", "insert_after", "delete"]


@dataclass
class Locator:
    paragraphIndex: int | None = None
    beforeAnchor: str | None = None
    afterAnchor: str | None = None


@dataclass
class ChangeItem:
    id: str
    chapterIndex: int
    chapterTitle: str
    kind: ChangeKind
    locator: Locator
    beforeText: str | None
    afterText: str | None
    reason: str
    risk: str | None = None

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "ChangeItem":
        loc = d.get("locator") or {}
        return ChangeItem(
            id=str(d.get("id") or ""),
            chapterIndex=int(d.get("chapterIndex") or 0),
            chapterTitle=str(d.get("chapterTitle") or ""),
            kind=str(d.get("kind") or "replace"),  # type: ignore[assignment]
            locator=Locator(
                paragraphIndex=loc.get("paragraphIndex"),
                beforeAnchor=loc.get("beforeAnchor"),
                afterAnchor=loc.get("afterAnchor"),
            ),
            beforeText=(d.get("beforeText") if d.get("beforeText") is not None else None),
            afterText=(d.get("afterText") if d.get("afterText") is not None else None),
            reason=str(d.get("reason") or ""),
            risk=(str(d.get("risk")) if d.get("risk") is not None else None),
        )


@dataclass
class ApplyResult:
    applied: bool
    new_text: str
    message: str = ""


def _paragraph_spans(text: str) -> list[tuple[int, int]]:
    """
    Returns (start, end) spans for paragraphs.
    Paragraphs are split by one or more blank lines.
    """
    if not text:
        return []
    spans: list[tuple[int, int]] = []
    n = len(text)
    i = 0
    while i < n:
        # skip leading blank lines
        while i < n and text[i] in "\r\n":
            i += 1
        if i >= n:
            break
        start = i
        # advance until blank line block
        while i < n:
            if text[i] == "\n":
                # check blank line (next char newline) or CRLF patterns
                j = i
                # consume consecutive newlines
                while j < n and text[j] == "\n":
                    j += 1
                # if we had 2+ newlines, paragraph ended at i
                if j - i >= 2:
                    break
            i += 1
        end = i
        spans.append((start, end))
        # consume blank line separators
        while i < n and text[i] in "\r\n":
            i += 1
    return spans


def _apply_with_paragraph_index(original: str, change: ChangeItem) -> ApplyResult | None:
    idx = change.locator.paragraphIndex
    if idx is None:
        return None
    spans = _paragraph_spans(original)
    if not spans:
        return ApplyResult(False, original, "正文无段落可定位。")
    if idx < 0 or idx >= len(spans):
        return ApplyResult(False, original, f"paragraphIndex 越界：{idx}（总段落 {len(spans)}）")

    start, end = spans[idx]
    para = original[start:end]
    before = (change.beforeText or "").strip()
    after = (change.afterText or "").rstrip()

    if change.kind in ("replace", "delete"):
        if not before:
            return ApplyResult(False, original, "缺少 beforeText，拒绝应用。")
        count = para.count(before)
        if count != 1:
            return ApplyResult(False, original, "段内匹配不唯一/不存在，拒绝应用。")
        if change.kind == "delete":
            new_para = para.replace(before, "", 1)
        else:
            if not after:
                return ApplyResult(False, original, "缺少 afterText，拒绝应用。")
            new_para = para.replace(before, after, 1)
        return ApplyResult(True, original[:start] + new_para + original[end:], "已按段落索引应用。")

    if change.kind in ("insert_before", "insert_after"):
        anchor = (change.locator.beforeAnchor or change.locator.afterAnchor or "").strip() or before
        if not anchor:
            return ApplyResult(False, original, "缺少锚点，拒绝应用。")
        count = para.count(anchor)
        if count != 1:
            return ApplyResult(False, original, "段内锚点匹配不唯一/不存在，拒绝应用。")
        if not after:
            return ApplyResult(False, original, "缺少 afterText，拒绝应用。")
        rel = para.find(anchor)
        if change.kind == "insert_before":
            new_para = para[:rel] + after + "\n" + para[rel:]
        else:
            rel_end = rel + len(anchor)
            new_para = para[:rel_end] + "\n" + after + para[rel_end:]
        return ApplyResult(True, original[:start] + new_para + original[end:], "已按段落索引应用。")

    return ApplyResult(False, original, f"不支持的改动类型：{change.kind}")


def _apply_with_anchor_window(original: str, change: ChangeItem) -> ApplyResult | None:
    """
    If both beforeAnchor and afterAnchor exist and are uniquely found in the text,
    use the window between them to disambiguate matches.
    """
    before_anchor = (change.locator.beforeAnchor or "").strip()
    after_anchor = (change.locator.afterAnchor or "").strip()
    if not before_anchor or not after_anchor:
        return None

    if original.count(before_anchor) != 1 or original.count(after_anchor) != 1:
        return ApplyResult(False, original, "锚点不唯一/不存在，无法使用锚点窗口定位。")

    a = original.find(before_anchor)
    b = original.find(after_anchor)
    if b <= a:
        return ApplyResult(False, original, "锚点顺序异常（afterAnchor 在 beforeAnchor 之前）。")

    win_start = a + len(before_anchor)
    win_end = b
    window = original[win_start:win_end]

    before = (change.beforeText or "").strip()
    after = (change.afterText or "").rstrip()

    if change.kind in ("replace", "delete"):
        if not before:
            return ApplyResult(False, original, "缺少 beforeText，拒绝应用。")
        if window.count(before) != 1:
            return ApplyResult(False, original, "锚点窗口内匹配不唯一/不存在，拒绝应用。")
        rel = window.find(before)
        abs_start = win_start + rel
        abs_end = abs_start + len(before)
        if change.kind == "delete":
            return ApplyResult(True, original[:abs_start] + original[abs_end:], "已在锚点窗口内删除。")
        if not after:
            return ApplyResult(False, original, "缺少 afterText，拒绝应用。")
        return ApplyResult(True, original[:abs_start] + after + original[abs_end:], "已在锚点窗口内替换。")

    if change.kind == "insert_before":
        if not after:
            return ApplyResult(False, original, "缺少 afterText，拒绝应用。")
        return ApplyResult(True, original[:win_start] + "\n" + after + original[win_start:], "已在锚点窗口起点插入。")

    if change.kind == "insert_after":
        if not after:
            return ApplyResult(False, original, "缺少 afterText，拒绝应用。")
        return ApplyResult(True, original[:win_end] + after + "\n" + original[win_end:], "已在锚点窗口终点插入。")

    return None


def apply_change(original: str, change: ChangeItem) -> ApplyResult:
    """
    MVP安全策略：
    - replace/delete：要求 beforeText 在正文中出现且仅出现一次，才会应用
    - insert_*：基于锚点插入（若锚点唯一匹配），否则拒绝
    """
    by_para = _apply_with_paragraph_index(original, change)
    if by_para is not None:
        return by_para

    by_window = _apply_with_anchor_window(original, change)
    if by_window is not None:
        return by_window

    text = original
    before = (change.beforeText or "").strip()
    after = (change.afterText or "").rstrip()

    if change.kind in ("replace", "delete"):
        if not before:
            return ApplyResult(False, original, "缺少 beforeText，拒绝应用。")
        count = text.count(before)
        if count == 0:
            return ApplyResult(False, original, "未找到 beforeText，可能已被修改，拒绝应用。")
        if count > 1:
            return ApplyResult(False, original, "beforeText 多处匹配，定位不唯一，拒绝应用。")
        if change.kind == "delete":
            return ApplyResult(True, text.replace(before, "", 1), "已删除匹配片段。")
        # replace
        if not after:
            return ApplyResult(False, original, "缺少 afterText，拒绝应用。")
        return ApplyResult(True, text.replace(before, after, 1), "已替换匹配片段。")

    if change.kind in ("insert_before", "insert_after"):
        anchor = (change.locator.beforeAnchor or change.locator.afterAnchor or "").strip()
        if not anchor:
            # try beforeText as anchor
            anchor = before
        if not anchor:
            return ApplyResult(False, original, "缺少锚点，拒绝应用。")
        count = text.count(anchor)
        if count == 0:
            return ApplyResult(False, original, "未找到锚点，拒绝应用。")
        if count > 1:
            return ApplyResult(False, original, "锚点多处匹配，定位不唯一，拒绝应用。")
        if not after:
            return ApplyResult(False, original, "缺少 afterText，拒绝应用。")

        idx = text.find(anchor)
        if change.kind == "insert_before":
            return ApplyResult(True, text[:idx] + after + "\n" + text[idx:], "已在锚点前插入。")
        # insert_after
        end = idx + len(anchor)
        return ApplyResult(True, text[:end] + "\n" + after + text[end:], "已在锚点后插入。")

    return ApplyResult(False, original, f"不支持的改动类型：{change.kind}")

