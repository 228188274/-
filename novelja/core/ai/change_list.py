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


def apply_change(original: str, change: ChangeItem) -> ApplyResult:
    """
    MVP安全策略：
    - replace/delete：要求 beforeText 在正文中出现且仅出现一次，才会应用
    - insert_*：基于锚点插入（若锚点唯一匹配），否则拒绝
    """
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

