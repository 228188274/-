from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Literal


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


ChapterStatus = Literal["draft", "submitted"]


@dataclass
class ChapterMeta:
    id: str
    index: int
    title: str
    status: ChapterStatus = "draft"
    file: str = ""
    wordCount: int = 0
    lastModifiedAt: str = field(default_factory=now_iso)
    lastSubmittedAt: str | None = None
    lastSnapshotId: str | None = None


@dataclass
class ProjectSettings:
    autosaveEnabled: bool = True
    autosaveSeconds: int = 10
    aiProvider: str = "deepseek"
    aiModel: str = ""


@dataclass
class Project:
    id: str
    title: str
    createdAt: str = field(default_factory=now_iso)
    updatedAt: str = field(default_factory=now_iso)
    chapterOrder: list[str] = field(default_factory=list)
    chapters: dict[str, ChapterMeta] = field(default_factory=dict)
    settings: ProjectSettings = field(default_factory=ProjectSettings)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # dataclasses.asdict already converts nested dataclasses
        return d

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Project":
        settings = ProjectSettings(**data.get("settings", {}))
        chapters_raw = data.get("chapters", {}) or {}
        chapters = {cid: ChapterMeta(**c) for cid, c in chapters_raw.items()}
        return Project(
            id=data["id"],
            title=data["title"],
            createdAt=data.get("createdAt", now_iso()),
            updatedAt=data.get("updatedAt", now_iso()),
            chapterOrder=list(data.get("chapterOrder", [])),
            chapters=chapters,
            settings=settings,
        )

