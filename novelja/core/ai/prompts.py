from __future__ import annotations


def polish_prompt(text: str) -> str:
    return (
        "你是专业中文小说编辑。请在不改变剧情信息、不新增设定的前提下润色以下文本：\n"
        "- 保持原叙述视角与人称\n"
        "- 优化语句通顺、节奏、措辞\n"
        "- 不要加入任何解释或评价\n\n"
        "输出：只输出润色后的正文。\n\n"
        f"正文：\n{text}"
    )


def summarize_prompt(text: str, max_chars: int = 500) -> str:
    return (
        "请将以下章节内容总结成便于作者回溯的摘要：\n"
        f"- 摘要长度不超过{max_chars}字\n"
        "- 提取关键事件、人物动机、悬念点\n"
        "- 不要写评价\n\n"
        "输出：只输出摘要。\n\n"
        f"正文：\n{text}"
    )


def next_preview_prompt(current_chapter_text: str, previous_summaries: str = "") -> str:
    ctx = f"\n\n已写内容摘要（可参考）：\n{previous_summaries}\n" if previous_summaries.strip() else ""
    return (
        "你是长篇小说策划编辑。根据已写章节，生成“下一章节预告/写作方向指引”。\n"
        "- 1段推进与冲突\n"
        "- 1段人物选择与动机\n"
        "- 1句悬念钩子\n"
        "- 尽量保持与正文一致的文风\n"
        "- 不要输出标题以外的多余说明\n\n"
        "输出：直接输出预告文本。\n"
        f"{ctx}\n"
        f"当前章节正文：\n{current_chapter_text}"
    )


def agent_change_list_prompt(book_text: str) -> str:
    return (
        "你是小说编辑智能体。你将对全书进行最小必要的统一优化（文风一致/逻辑一致/可读性）。\n"
        "重要：不要直接输出修改后的整本正文，只输出 JSON 格式的 changeList。\n"
        "changeList 结构：\n"
        "- id: string\n"
        "- chapterIndex: number\n"
        "- chapterTitle: string\n"
        "- kind: replace | insert_before | insert_after | delete\n"
        "- locator: { paragraphIndex?: number, beforeAnchor?: string, afterAnchor?: string }\n"
        "- beforeText?: string\n"
        "- afterText?: string\n"
        "- reason: string\n"
        "- risk?: low | medium | high\n\n"
        "定位要求（请严格遵守，便于程序自动应用）：\n"
        "- 优先提供 locator.paragraphIndex：章节内段落索引，从 0 开始；段落以“空行分隔”。\n"
        "- 同时尽量提供 beforeAnchor 与 afterAnchor：分别为改动位置前后各 10~30 字的原文片段（必须来自原文，且尽量唯一）。\n"
        "- beforeText/afterText 只给“要改的那一小段”，不要给整章大段落。\n"
        "- 如果你无法给出稳定定位（段落索引不确定/锚点会重复），请不要输出该条改动。\n\n"
        "约束：\n"
        "- 不改变关键剧情走向\n"
        "- 不替换专有名词（人名/地名/功法等）\n"
        "- 以“最小改动”修复矛盾与语病\n\n"
        "输出要求：\n"
        "- 只输出一个 JSON 对象：{ \"changeList\": [ ... ] }\n"
        "- JSON 必须可被严格解析\n\n"
        f"全书内容（按章节）：\n{book_text}"
    )

