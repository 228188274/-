from __future__ import annotations

import json
import re
import shutil
import time
import uuid
from dataclasses import replace
from pathlib import Path

from platformdirs import user_data_dir

from novelja.core.models import ChapterMeta, Project, ProjectSettings, now_iso
from novelja.core.security import load_default_autosave


DEFAULT_CHAPTER_TITLE = "第{n}章"


def default_app_data_root() -> Path:
    # e.g. Linux: ~/.local/share/novelja/novelja
    return Path(user_data_dir(appname="novelja", appauthor="novelja"))


def safe_project_dir_name(title: str) -> str:
    cleaned = re.sub(r"[^\w\u4e00-\u9fff\- ]+", "", title).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned or "novel"


class ProjectStore:
    """
    Local-first project storage using a folder + JSON + markdown chapter files.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or default_app_data_root()
        self.root.mkdir(parents=True, exist_ok=True)

    def list_projects(self) -> list[Path]:
        return sorted([p for p in self.root.iterdir() if p.is_dir()])

    def create_project(self, title: str) -> Path:
        project_id = str(uuid.uuid4())
        folder = self.root / f"{safe_project_dir_name(title)}_{project_id[:8]}"
        folder.mkdir(parents=True, exist_ok=False)
        (folder / "chapters").mkdir()
        (folder / "previews").mkdir()
        (folder / "versions" / "snapshots").mkdir(parents=True)
        (folder / "versions" / "agent-runs").mkdir(parents=True)
        (folder / "cache").mkdir()

        autosave_enabled, autosave_seconds = load_default_autosave()
        project = Project(
            id=project_id,
            title=title,
            settings=ProjectSettings(autosaveEnabled=autosave_enabled, autosaveSeconds=autosave_seconds),
        )
        self._write_project(folder, project)
        return folder

    def load_project(self, folder: Path) -> Project:
        data = json.loads((folder / "project.json").read_text(encoding="utf-8"))
        return Project.from_dict(data)

    def save_project(self, folder: Path, project: Project) -> None:
        project.updatedAt = now_iso()
        self._write_project(folder, project)

    def _write_project(self, folder: Path, project: Project) -> None:
        (folder / "project.json").write_text(
            json.dumps(project.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _chapter_file_name(self, index: int) -> str:
        return f"{index:04d}.md"

    def new_chapter(self, folder: Path, project: Project, title: str | None = None) -> Project:
        next_index = 1
        if project.chapterOrder:
            indices = [project.chapters[cid].index for cid in project.chapterOrder if cid in project.chapters]
            next_index = (max(indices) + 1) if indices else 1

        chapter_id = str(uuid.uuid4())
        chapter_title = title or DEFAULT_CHAPTER_TITLE.format(n=next_index)
        file_rel = f"chapters/{self._chapter_file_name(next_index)}"
        file_path = folder / file_rel
        file_path.write_text("", encoding="utf-8")

        meta = ChapterMeta(
            id=chapter_id,
            index=next_index,
            title=chapter_title,
            status="draft",
            file=file_rel,
            wordCount=0,
            lastModifiedAt=now_iso(),
        )
        project.chapterOrder.append(chapter_id)
        project.chapters[chapter_id] = meta
        self.save_project(folder, project)
        return project

    def read_chapter_text(self, folder: Path, project: Project, chapter_id: str) -> str:
        meta = project.chapters[chapter_id]
        path = folder / meta.file
        if not path.exists():
            return ""
        return path.read_text(encoding="utf-8")

    def write_chapter_text(self, folder: Path, project: Project, chapter_id: str, text: str) -> Project:
        meta = project.chapters[chapter_id]
        (folder / meta.file).write_text(text, encoding="utf-8")
        # Chinese-friendly word count: count non-whitespace characters
        word_count = len(re.sub(r"\s+", "", text)) if text else 0
        updated = replace(meta, wordCount=word_count, lastModifiedAt=now_iso())
        project.chapters[chapter_id] = updated
        self.save_project(folder, project)
        return project

    def write_next_preview(self, folder: Path, chapter_index: int, text: str) -> None:
        (folder / "previews" / f"{chapter_index:04d}_next.md").write_text(text, encoding="utf-8")

    def read_next_preview(self, folder: Path, chapter_index: int) -> str:
        p = folder / "previews" / f"{chapter_index:04d}_next.md"
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def mark_submitted(self, folder: Path, project: Project, chapter_id: str) -> tuple[Project, str]:
        """
        Create snapshot and mark the chapter as submitted.
        Returns (updated project, snapshotId)
        """
        snapshot_id = self.create_snapshot(folder, project, reason=f"submit:{chapter_id}")
        meta = project.chapters[chapter_id]
        updated = replace(meta, status="submitted", lastSubmittedAt=now_iso(), lastSnapshotId=snapshot_id)
        project.chapters[chapter_id] = updated
        self.save_project(folder, project)
        return project, snapshot_id

    def create_snapshot(self, folder: Path, project: Project, reason: str = "") -> str:
        snapshot_id = f"{uuid.uuid4().hex[:8]}_{time.time_ns()}"
        snap_root = folder / "versions" / "snapshots" / snapshot_id
        snap_root.mkdir(parents=True, exist_ok=False)

        # copy project.json
        shutil.copy2(folder / "project.json", snap_root / "project.json")
        # copy chapters folder
        shutil.copytree(folder / "chapters", snap_root / "chapters")
        # write metadata
        (snap_root / "meta.json").write_text(
            json.dumps({"createdAt": now_iso(), "reason": reason}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return snapshot_id

    def restore_snapshot(self, folder: Path, snapshot_id: str) -> None:
        snap_root = folder / "versions" / "snapshots" / snapshot_id
        if not snap_root.exists():
            raise FileNotFoundError(f"snapshot not found: {snapshot_id}")

        shutil.copy2(snap_root / "project.json", folder / "project.json")
        # replace chapters completely
        chapters_dir = folder / "chapters"
        if chapters_dir.exists():
            shutil.rmtree(chapters_dir)
        shutil.copytree(snap_root / "chapters", chapters_dir)

