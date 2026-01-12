from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QWidget,
    QVBoxLayout,
)

from novelja.core.ai.change_list import ChangeItem, apply_change
from novelja.core.ai.client import ai_agent_change_list, load_ai_context
from novelja.core.storage import ProjectStore
from novelja.ui.async_worker import BackgroundTask
from novelja.ui.app_state import CurrentProject, get_app_state


class AgentTab(QWidget):
    """
    智能体模式（MVP实现）：
    - 打开作品 -> 读取全书 -> 生成 changeList（AI输出JSON） -> 列表审阅
    - 仅对“定位唯一”的改动执行安全应用（默认要求 beforeText 唯一匹配）
    - 应用前创建快照，可回滚到应用前
    """

    def __init__(self) -> None:
        super().__init__()

        self.store = ProjectStore()
        self.project_dir: Path | None = None
        self.project = None
        self.last_snapshot_id: str | None = None

        root = QVBoxLayout(self)
        header = QLabel("智能体模式：全章节统筹优化 + 改动记录清单（可审阅/可应用/可回滚）")
        header.setAlignment(Qt.AlignLeft)
        root.addWidget(header)

        row0 = QHBoxLayout()
        self.btn_open_project = QPushButton("打开作品")
        self.project_label = QLabel("未打开作品")
        self.project_label.setStyleSheet("color: #666;")
        row0.addWidget(self.btn_open_project)
        row0.addWidget(self.project_label, 1)
        root.addLayout(row0)

        box = QGroupBox("优化目标")
        form = QFormLayout(box)
        self.goal = QComboBox()
        self.goal.addItems(["风格统一/语言润色", "逻辑一致性修复", "节奏与可读性优化"])
        form.addRow("目标", self.goal)
        root.addWidget(box)

        root.addWidget(QLabel("改动记录清单（勾选后可应用）："))
        self.change_list = QListWidget()
        root.addWidget(self.change_list, 1)

        row = QHBoxLayout()
        self.btn_generate = QPushButton("生成改动清单")
        self.btn_apply = QPushButton("应用勾选改动")
        self.btn_apply_all = QPushButton("全部应用")
        self.btn_rollback = QPushButton("回滚到应用前快照")
        row.addWidget(self.btn_generate)
        row.addWidget(self.btn_apply)
        row.addWidget(self.btn_apply_all)
        row.addWidget(self.btn_rollback)
        row.addStretch(1)
        root.addLayout(row)

        self.btn_open_project.clicked.connect(self._open_project)
        self.btn_generate.clicked.connect(self._generate)
        self.btn_apply.clicked.connect(self._apply_checked)
        self.btn_apply_all.clicked.connect(self._apply_all)
        self.btn_rollback.clicked.connect(self._rollback)

        self._set_enabled(False)

        # auto-follow current project opened in "开始创作"
        get_app_state().projectChanged.connect(self._on_global_project_changed)
        current = get_app_state().current_project()
        if current:
            self._use_project(current)

    def _set_enabled(self, enabled: bool) -> None:
        self.btn_generate.setEnabled(enabled)
        self.btn_apply.setEnabled(enabled)
        self.btn_apply_all.setEnabled(enabled)
        self.btn_rollback.setEnabled(enabled and bool(self.last_snapshot_id))

    def _ensure_project_open(self) -> bool:
        if self.project_dir is None or self.project is None:
            QMessageBox.warning(self, "提示", "请先在本页打开一个作品目录。")
            return False
        return True

    def _open_project(self) -> None:
        folder_str = QFileDialog.getExistingDirectory(self, "选择作品文件夹")
        if not folder_str:
            return
        folder = Path(folder_str)
        if not (folder / "project.json").exists():
            QMessageBox.warning(self, "无法打开", "所选文件夹不包含 project.json，可能不是小说佳作品目录。")
            return
        self.project_dir = folder
        self.project = self.store.load_project(folder)
        self.project_label.setText(f"{self.project.title}  ({folder})")
        self.change_list.clear()
        self.last_snapshot_id = None
        self._set_enabled(True)
        get_app_state().set_current_project(folder, self.project)

    def _on_global_project_changed(self, current: object) -> None:
        if current is None:
            return
        if isinstance(current, CurrentProject):
            self._use_project(current)

    def _use_project(self, current: CurrentProject) -> None:
        self.project_dir = current.folder
        # Reload from disk to ensure consistency (agent writes happen here too)
        try:
            self.project = self.store.load_project(current.folder)
        except Exception:
            self.project = current.project
        self.project_label.setText(f"{self.project.title}  ({self.project_dir})")
        self._set_enabled(True)

    def _book_text(self) -> str:
        # Provide chapters with stable headers, helping AI reference chapterIndex/title.
        parts: list[str] = []
        by_index = sorted(self.project.chapters.values(), key=lambda m: m.index)
        for meta in by_index:
            cid = meta.id
            # Find chapter id by index via chapterOrder mapping (meta.id is stored); use read by id.
            try:
                # meta.id is chapterId
                text = self.store.read_chapter_text(self.project_dir, self.project, cid)  # type: ignore[arg-type]
            except Exception:
                text = ""
            parts.append(f"## Chapter {meta.index}: {meta.title}\n\n{text.strip()}\n")
        return "\n".join(parts).strip()

    def _generate(self) -> None:
        if not self._ensure_project_open():
            return
        if not load_ai_context():
            QMessageBox.warning(self, "未配置AI", "请先在“API密钥”页配置并测试连通性。")
            return
        book = self._book_text()
        if not book:
            QMessageBox.information(self, "提示", "作品内容为空。")
            return

        self.btn_generate.setEnabled(False)
        self.btn_generate.setText("生成中…")
        self.change_list.clear()
        self.change_list.addItem("生成中…")

        def work() -> list[dict]:
            return ai_agent_change_list(book)

        def ok(changes: list[dict]) -> None:
            self.btn_generate.setEnabled(True)
            self.btn_generate.setText("生成改动清单")
            self.change_list.clear()
            if not changes:
                self.change_list.addItem("（无改动）")
                return
            for d in changes:
                try:
                    item = ChangeItem.from_dict(d)
                except Exception:
                    continue
                label = f"[{item.chapterIndex}] {item.chapterTitle} | {item.kind} | {item.reason}"
                li = QListWidgetItem(label)
                li.setFlags(li.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                li.setCheckState(Qt.Checked)
                li.setData(Qt.UserRole, d)
                self.change_list.addItem(li)

            # Persist agent run record (optional but useful)
            self._write_agent_run(changes)

        def err(e: Exception) -> None:
            self.btn_generate.setEnabled(True)
            self.btn_generate.setText("生成改动清单")
            self.change_list.clear()
            QMessageBox.warning(self, "生成失败", str(e))

        BackgroundTask(func=work, on_success=ok, on_error=err).start()

    def _write_agent_run(self, changes: list[dict]) -> None:
        if not self._ensure_project_open():
            return
        run_id = f"{uuid.uuid4().hex[:8]}_{int(time.time())}"
        out = {
            "id": run_id,
            "createdAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "goal": self.goal.currentText(),
            "changeList": changes,
        }
        path = self.project_dir / "versions" / "agent-runs" / f"{run_id}.json"
        try:
            path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _apply_all(self) -> None:
        if not self._ensure_project_open():
            return
        for i in range(self.change_list.count()):
            it = self.change_list.item(i)
            if it and (it.flags() & Qt.ItemIsUserCheckable):
                it.setCheckState(Qt.Checked)
        self._apply_checked()

    def _apply_checked(self) -> None:
        if not self._ensure_project_open():
            return
        # collect checked changes
        payloads: list[dict] = []
        for i in range(self.change_list.count()):
            it = self.change_list.item(i)
            if not it:
                continue
            if it.checkState() == Qt.Checked:
                d = it.data(Qt.UserRole)
                if isinstance(d, dict):
                    payloads.append(d)
        if not payloads:
            QMessageBox.information(self, "提示", "没有勾选任何改动。")
            return

        # snapshot before apply
        snapshot_id = self.store.create_snapshot(self.project_dir, self.project, reason="agent_apply")  # type: ignore[arg-type]
        self.last_snapshot_id = snapshot_id
        self._set_enabled(True)

        # Build index -> chapterId mapping
        index_to_id: dict[int, str] = {}
        for cid in self.project.chapterOrder:
            meta = self.project.chapters.get(cid)
            if meta:
                index_to_id[meta.index] = cid

        applied = 0
        conflicts: list[str] = []
        for d in payloads:
            try:
                change = ChangeItem.from_dict(d)
            except Exception:
                continue
            cid = index_to_id.get(change.chapterIndex)
            if not cid:
                conflicts.append(f"找不到章节索引：{change.chapterIndex}")
                continue
            original = self.store.read_chapter_text(self.project_dir, self.project, cid)  # type: ignore[arg-type]
            res = apply_change(original, change)
            if not res.applied:
                conflicts.append(f"[{change.chapterIndex}] {change.reason} -> {res.message}")
                continue
            self.project = self.store.write_chapter_text(self.project_dir, self.project, cid, res.new_text)  # type: ignore[arg-type]
            applied += 1

        msg = f"已应用 {applied} 条改动。\n快照ID：{snapshot_id}"
        if conflicts:
            msg += "\n\n未应用/冲突：\n" + "\n".join(conflicts[:20])
            if len(conflicts) > 20:
                msg += f"\n… 共 {len(conflicts)} 条冲突"
        QMessageBox.information(self, "应用结果", msg)

    def _rollback(self) -> None:
        if not self._ensure_project_open():
            return
        if not self.last_snapshot_id:
            QMessageBox.information(self, "提示", "暂无可回滚的快照。")
            return
        r = QMessageBox.question(self, "确认回滚", f"将回滚到快照：{self.last_snapshot_id}\n是否继续？")
        if r != QMessageBox.Yes:
            return
        try:
            self.store.restore_snapshot(self.project_dir, self.last_snapshot_id)  # type: ignore[arg-type]
            self.project = self.store.load_project(self.project_dir)
        except Exception as e:
            QMessageBox.warning(self, "回滚失败", str(e))
            return
        QMessageBox.information(self, "回滚完成", f"已回滚到快照：{self.last_snapshot_id}")
        self._set_enabled(True)
