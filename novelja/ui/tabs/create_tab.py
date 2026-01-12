from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from novelja.core.ai.client import ai_next_preview, ai_polish, ai_summarize, load_ai_context
from novelja.core.import_export import export_chapters_to_markdown, read_text_file, split_book_to_chapters
from novelja.core.security import load_recent_projects, prune_recent_projects
from novelja.core.storage import ProjectStore
from novelja.ui.async_worker import BackgroundTask
from novelja.ui.app_state import get_app_state
from novelja.ui.dialogs.backtrack_dialog import BacktrackDialog
from novelja.ui.dialogs.polish_dialog import PolishCompareDialog


class CreateTab(QWidget):
    """
    开始创作（MVP）：
    - 本地作品/章节管理
    - 编辑器 + 自动保存
    - 章节提交（创建快照）+ 生成“下一章节预告”（先用规则占位，后续接AI）
    """

    def __init__(self) -> None:
        super().__init__()

        self.store = ProjectStore()
        self.project_dir: Path | None = None
        self.project = None  # loaded Project
        self.current_chapter_id: str | None = None
        self._loading = False
        self._dirty = False

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.timeout.connect(self._autosave_if_needed)

        self._backtrack_dialog: BacktrackDialog | None = None

        root = QHBoxLayout(self)
        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter)

        # Left: project + chapter management
        left = QWidget()
        left_layout = QVBoxLayout(left)

        row0 = QHBoxLayout()
        self.btn_new_project = QPushButton("新建作品")
        self.btn_open_project = QPushButton("打开作品")
        self.btn_new_project.setProperty("variant", "primary")
        row0.addWidget(self.btn_new_project)
        row0.addWidget(self.btn_open_project)
        left_layout.addLayout(row0)

        row1 = QHBoxLayout()
        self.btn_new_chapter = QPushButton("+ 新建章节")
        self.btn_import = QPushButton("导入")
        self.btn_export = QPushButton("导出")
        row1.addWidget(self.btn_new_chapter)
        row1.addWidget(self.btn_import)
        row1.addWidget(self.btn_export)
        left_layout.addLayout(row1)

        self.project_name = QLabel("当前作品：未打开")
        self.project_name.setWordWrap(True)
        left_layout.addWidget(self.project_name)

        self.recent_label = QLabel("最近作品（双击打开）：")
        self.recent_label.setStyleSheet("color: #666;")
        left_layout.addWidget(self.recent_label)

        self.recent_list = QListWidget()
        left_layout.addWidget(self.recent_list)

        recent_actions = QHBoxLayout()
        self.btn_recent_cleanup = QPushButton("清理无效")
        recent_actions.addWidget(self.btn_recent_cleanup)
        recent_actions.addStretch(1)
        left_layout.addLayout(recent_actions)

        self.chapter_filter = QLineEdit()
        self.chapter_filter.setPlaceholderText("搜索章节（标题关键词）")
        left_layout.addWidget(self.chapter_filter)

        self.chapter_list = QListWidget()
        left_layout.addWidget(self.chapter_list, 1)

        splitter.addWidget(left)

        # Right: editor + tools + preview
        right = QWidget()
        right_layout = QVBoxLayout(right)

        self.chapter_title = QLineEdit()
        self.chapter_title.setPlaceholderText("章节标题（例如：第1章 初遇）")
        right_layout.addWidget(self.chapter_title)

        self.chapter_meta = QLabel("未选择章节")
        self.chapter_meta.setStyleSheet("color: #666;")
        right_layout.addWidget(self.chapter_meta)

        tool_row = QHBoxLayout()
        self.btn_polish = QPushButton("AI润色")
        self.btn_backtrack = QPushButton("回溯阅读")
        self.btn_submit = QPushButton("确认保存（提交）")
        self.btn_submit.setProperty("variant", "primary")
        tool_row.addWidget(self.btn_polish)
        tool_row.addWidget(self.btn_backtrack)
        tool_row.addStretch(1)
        tool_row.addWidget(self.btn_submit)
        right_layout.addLayout(tool_row)

        self.editor = QPlainTextEdit()
        self.editor.setPlaceholderText("在这里开始写作…")
        right_layout.addWidget(self.editor, 2)

        right_layout.addWidget(QLabel("下一章节预告（提交后自动生成，可编辑）："))
        self.next_preview = QPlainTextEdit()
        self.next_preview.setPlaceholderText("提交章节后，这里会自动生成下一章预告…")
        right_layout.addWidget(self.next_preview, 1)

        splitter.addWidget(right)
        splitter.setSizes([320, 880])

        # wiring
        self.btn_new_project.clicked.connect(self._new_project)
        self.btn_open_project.clicked.connect(self._open_project)
        self.btn_new_chapter.clicked.connect(self._new_chapter)
        self.btn_import.clicked.connect(self._import_file)
        self.btn_export.clicked.connect(self._export_file)

        self.chapter_filter.textChanged.connect(self._refresh_chapter_list)
        self.chapter_list.currentItemChanged.connect(self._on_chapter_selected)
        self.chapter_title.editingFinished.connect(self._on_title_edited)

        self.editor.textChanged.connect(self._on_editor_changed)
        self.next_preview.textChanged.connect(self._on_preview_changed)

        self.btn_submit.clicked.connect(self._submit_chapter)
        self.btn_polish.clicked.connect(self._ai_polish)
        self.btn_backtrack.clicked.connect(self._backtrack)

        self._set_enabled(False)
        self._refresh_recent_projects()
        get_app_state().projectChanged.connect(lambda _: self._refresh_recent_projects())
        self.recent_list.itemDoubleClicked.connect(self._open_recent_item)
        self.btn_recent_cleanup.clicked.connect(self._cleanup_recent_projects)

    def _set_enabled(self, enabled: bool) -> None:
        self.btn_new_chapter.setEnabled(enabled)
        self.btn_import.setEnabled(enabled)
        self.btn_export.setEnabled(enabled)
        self.chapter_filter.setEnabled(enabled)
        self.chapter_list.setEnabled(enabled)

        editor_enabled = enabled and self.current_chapter_id is not None
        self.chapter_title.setEnabled(editor_enabled)
        self.editor.setEnabled(editor_enabled)
        self.btn_submit.setEnabled(editor_enabled)
        self.btn_polish.setEnabled(editor_enabled)
        self.btn_backtrack.setEnabled(editor_enabled)
        self.next_preview.setEnabled(editor_enabled)

        no_project = self.project_dir is None or self.project is None
        self.recent_label.setVisible(no_project)
        self.recent_list.setVisible(no_project)
        self.btn_recent_cleanup.setVisible(no_project)

    def _ensure_project_open(self) -> bool:
        if self.project_dir is None or self.project is None:
            QMessageBox.warning(self, "提示", "请先新建或打开一个作品。")
            return False
        return True

    def _new_project(self) -> None:
        title, ok = QInputDialog.getText(self, "新建作品", "作品名称：")
        if not ok or not title.strip():
            return
        folder = self.store.create_project(title.strip())
        self._load_project(folder)
        # create an initial chapter
        self.project = self.store.new_chapter(self.project_dir, self.project)  # type: ignore[arg-type]
        self._refresh_chapter_list()
        self.chapter_list.setCurrentRow(0)

    # Public helpers for main window menu actions
    def menu_new_project(self) -> None:
        self._new_project()

    def menu_open_project(self) -> None:
        self._open_project()

    def menu_import(self) -> None:
        self._import_file()

    def menu_export(self) -> None:
        self._export_file()

    def _open_project(self) -> None:
        folder_str = QFileDialog.getExistingDirectory(self, "选择作品文件夹")
        if not folder_str:
            return
        self.open_project_path(folder_str)

    def open_project_path(self, folder_str: str, *, silent: bool = False) -> None:
        folder = Path(folder_str)
        if not (folder / "project.json").exists():
            if not silent:
                QMessageBox.warning(self, "无法打开", "所选文件夹不包含 project.json，可能不是小说佳作品目录。")
            return
        self._load_project(folder)
        self._refresh_chapter_list()
        if self.chapter_list.count() > 0:
            self.chapter_list.setCurrentRow(0)

    def _refresh_recent_projects(self) -> None:
        # Only relevant when no project is open
        if self.project_dir is not None and self.project is not None:
            self.recent_list.clear()
            return
        self.recent_list.clear()
        for p in load_recent_projects():
            self.recent_list.addItem(p)
        if self.recent_list.count() == 0:
            self.recent_list.addItem("（暂无）")
            self.recent_list.item(0).setFlags(Qt.NoItemFlags)

    def _open_recent_item(self, item: QListWidgetItem) -> None:
        path = (item.text() or "").strip()
        if not path or path == "（暂无）":
            return
        self.open_project_path(path)

    def _cleanup_recent_projects(self) -> None:
        cleaned, changed = prune_recent_projects()
        if changed:
            QMessageBox.information(self, "已清理", f"已清理无效最近作品记录，剩余 {len(cleaned)} 条。")
        else:
            QMessageBox.information(self, "无需清理", "最近作品记录均有效。")
        self._refresh_recent_projects()

    def _load_project(self, folder: Path) -> None:
        self.project_dir = folder
        self.project = self.store.load_project(folder)
        self.project_name.setText(f"当前作品：{self.project.title}\n位置：{str(folder)}")
        self.current_chapter_id = None
        self._dirty = False
        self._set_enabled(True)
        get_app_state().set_current_project(folder, self.project)
        self._refresh_recent_projects()

    def _refresh_chapter_list(self) -> None:
        if not self._ensure_project_open():
            return
        self._loading = True
        try:
            filter_text = (self.chapter_filter.text() or "").strip()
            self.chapter_list.clear()
            for cid in self.project.chapterOrder:
                if cid not in self.project.chapters:
                    continue
                meta = self.project.chapters[cid]
                label = f"{meta.index:>3}. {meta.title}  [{'已提交' if meta.status == 'submitted' else '草稿'}]"
                if filter_text and filter_text not in meta.title:
                    continue
                item = QListWidgetItem(label)
                item.setData(Qt.UserRole, cid)
                self.chapter_list.addItem(item)
        finally:
            self._loading = False

    def _new_chapter(self) -> None:
        if not self._ensure_project_open():
            return
        self._autosave_if_needed()
        self.project = self.store.new_chapter(self.project_dir, self.project)  # type: ignore[arg-type]
        self._refresh_chapter_list()
        self.chapter_list.setCurrentRow(self.chapter_list.count() - 1)

    def _on_chapter_selected(self, current: QListWidgetItem | None, previous: QListWidgetItem | None) -> None:
        if self._loading:
            return
        if not self._ensure_project_open():
            return
        self._autosave_if_needed()

        if current is None:
            self.current_chapter_id = None
            self._set_enabled(True)
            return

        chapter_id = str(current.data(Qt.UserRole))
        self._load_chapter(chapter_id)

    def _load_chapter(self, chapter_id: str) -> None:
        self._loading = True
        try:
            self.current_chapter_id = chapter_id
            meta = self.project.chapters[chapter_id]
            text = self.store.read_chapter_text(self.project_dir, self.project, chapter_id)  # type: ignore[arg-type]

            self.chapter_title.setText(meta.title)
            self.editor.setPlainText(text)

            preview = self.store.read_next_preview(self.project_dir, meta.index)  # type: ignore[arg-type]
            self.next_preview.setPlainText(preview)

            self.chapter_meta.setText(
                f"状态：{'已提交' if meta.status == 'submitted' else '草稿'}    字数：{meta.wordCount}    最后修改：{meta.lastModifiedAt}"
            )
            self._dirty = False
            self._set_enabled(True)
        finally:
            self._loading = False

    def _on_title_edited(self) -> None:
        if self._loading or not self._ensure_project_open() or not self.current_chapter_id:
            return
        title = self.chapter_title.text().strip()
        if not title:
            return
        meta = self.project.chapters[self.current_chapter_id]
        if meta.title != title:
            meta.title = title
            self.project.chapters[self.current_chapter_id] = meta
            self.store.save_project(self.project_dir, self.project)  # type: ignore[arg-type]
            self._refresh_chapter_list()

    def _on_editor_changed(self) -> None:
        if self._loading:
            return
        self._dirty = True
        if self._ensure_project_open() and self.current_chapter_id:
            seconds = int(getattr(self.project.settings, "autosaveSeconds", 10) or 10)
            self.autosave_timer.start(max(2, seconds) * 1000)

    def _on_preview_changed(self) -> None:
        if self._loading:
            return
        if self._ensure_project_open() and self.current_chapter_id:
            self.autosave_timer.start(1500)

    def _autosave_if_needed(self) -> None:
        if not self._ensure_project_open() or not self.current_chapter_id:
            return
        if self._dirty:
            text = self.editor.toPlainText()
            self.project = self.store.write_chapter_text(self.project_dir, self.project, self.current_chapter_id, text)  # type: ignore[arg-type]
            self._dirty = False
        meta = self.project.chapters[self.current_chapter_id]
        self.store.write_next_preview(self.project_dir, meta.index, self.next_preview.toPlainText())  # type: ignore[arg-type]
        self.chapter_meta.setText(
            f"状态：{'已提交' if meta.status == 'submitted' else '草稿'}    字数：{meta.wordCount}    最后修改：{meta.lastModifiedAt}"
        )
        # keep global state fresh (lightweight)
        get_app_state().set_current_project(self.project_dir, self.project)  # type: ignore[arg-type]

    def _submit_chapter(self) -> None:
        if not self._ensure_project_open() or not self.current_chapter_id:
            return
        self._autosave_if_needed()

        if not self.editor.toPlainText().strip():
            r = QMessageBox.question(self, "确认提交", "当前章节内容为空，仍要提交吗？")
            if r != QMessageBox.Yes:
                return

        self.project, snapshot_id = self.store.mark_submitted(self.project_dir, self.project, self.current_chapter_id)  # type: ignore[arg-type]
        meta = self.project.chapters[self.current_chapter_id]

        # 自动生成下一章节预告：优先AI，否则使用规则占位
        if not self.next_preview.toPlainText().strip():
            if load_ai_context():
                self._loading = True
                try:
                    self.next_preview.setPlainText("生成中…")
                finally:
                    self._loading = False

                chapter_text = self.editor.toPlainText()
                prev_summary = self._previous_chapter_summary_fallback()

                def work() -> str:
                    return ai_next_preview(chapter_text, previous_summaries=prev_summary)

                def ok(preview: str) -> None:
                    self._loading = True
                    try:
                        self.next_preview.setPlainText(preview.strip())
                    finally:
                        self._loading = False
                    self.store.write_next_preview(self.project_dir, meta.index, preview.strip())  # type: ignore[arg-type]

                def err(e: Exception) -> None:
                    hint = "下一章预告：\n- 推进当前冲突\n- 让关键人物做出选择\n- 留下一个悬念钩子"
                    self._loading = True
                    try:
                        self.next_preview.setPlainText(hint)
                    finally:
                        self._loading = False
                    self.store.write_next_preview(self.project_dir, meta.index, hint)  # type: ignore[arg-type]
                    QMessageBox.warning(self, "预告生成失败", f"已使用占位预告。\n原因：{e}")

                BackgroundTask(func=work, on_success=ok, on_error=err).start()
            else:
                hint = "下一章预告：\n- 推进当前冲突\n- 让关键人物做出选择\n- 留下一个悬念钩子"
                self._loading = True
                try:
                    self.next_preview.setPlainText(hint)
                finally:
                    self._loading = False
                self.store.write_next_preview(self.project_dir, meta.index, hint)  # type: ignore[arg-type]

        QMessageBox.information(self, "提交成功", f"章节已提交并创建快照：{snapshot_id}")
        self._refresh_chapter_list()
        self._load_chapter(self.current_chapter_id)

    def _import_file(self) -> None:
        if not self._ensure_project_open():
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "导入小说文件", filter="Text/Markdown (*.txt *.md);;All files (*.*)")
        if not file_path:
            return
        try:
            text = read_text_file(Path(file_path))
        except Exception as e:
            QMessageBox.warning(self, "导入失败", f"无法读取文件：{e}")
            return

        result = split_book_to_chapters(text)
        for title, content in result.chapters:
            self.project = self.store.new_chapter(self.project_dir, self.project, title=title)  # type: ignore[arg-type]
            new_id = self.project.chapterOrder[-1]
            self.project = self.store.write_chapter_text(self.project_dir, self.project, new_id, content)  # type: ignore[arg-type]

        self._refresh_chapter_list()
        if result.warnings:
            QMessageBox.information(self, "导入完成", "\n".join(result.warnings))

    def _export_file(self) -> None:
        if not self._ensure_project_open():
            return
        out_path, _ = QFileDialog.getSaveFileName(self, "导出作品", filter="Markdown (*.md);;Text (*.txt)")
        if not out_path:
            return
        chapters: list[tuple[str, str]] = []
        for cid in self.project.chapterOrder:
            meta = self.project.chapters[cid]
            chapters.append((meta.title, self.store.read_chapter_text(self.project_dir, self.project, cid)))  # type: ignore[arg-type]
        md = export_chapters_to_markdown(chapters, include_toc=True)
        try:
            Path(out_path).write_text(md, encoding="utf-8")
        except Exception as e:
            QMessageBox.warning(self, "导出失败", f"无法写入文件：{e}")
            return
        QMessageBox.information(self, "导出成功", f"已导出到：{out_path}")

    def _ai_polish(self) -> None:
        if not self._ensure_project_open() or not self.current_chapter_id:
            return
        cursor = self.editor.textCursor()
        selected = cursor.selectedText()
        selected = selected.replace("\u2029", "\n")  # Qt selection line separator
        has_selection = bool(selected.strip())
        scope_text = selected.strip() if has_selection else self.editor.toPlainText()
        if not scope_text.strip():
            QMessageBox.information(self, "AI润色", "当前内容为空。")
            return
        if not load_ai_context():
            QMessageBox.warning(self, "未配置AI", "请先在“API密钥”页配置并测试连通性。")
            return

        self.btn_polish.setEnabled(False)
        self.btn_polish.setText("润色中…")

        def work() -> str:
            return ai_polish(scope_text)

        def ok(polished: str) -> None:
            self.btn_polish.setEnabled(True)
            self.btn_polish.setText("AI润色")
            dlg = PolishCompareDialog(scope_text, polished, parent=self)
            if dlg.exec() != dlg.Accepted:
                return

            action = dlg.chosen_action()
            out = dlg.polished_text()
            if action == "copy":
                return

            if action == "insert":
                c = self.editor.textCursor()
                c.insertText(out)
                self._dirty = True
                self._autosave_if_needed()
                return

            # default: replace
            if has_selection:
                c = self.editor.textCursor()
                c.insertText(out)  # replaces selection
            else:
                self._loading = True
                try:
                    self.editor.setPlainText(out)
                finally:
                    self._loading = False
            self._dirty = True
            self._autosave_if_needed()

        def err(e: Exception) -> None:
            self.btn_polish.setEnabled(True)
            self.btn_polish.setText("AI润色")
            QMessageBox.warning(self, "润色失败", str(e))

        BackgroundTask(func=work, on_success=ok, on_error=err).start()

    def _previous_chapter_id(self) -> str | None:
        if not self.current_chapter_id:
            return None
        order = list(self.project.chapterOrder)
        try:
            i = order.index(self.current_chapter_id)
        except ValueError:
            return None
        if i <= 0:
            return None
        return order[i - 1]

    def _previous_chapter_summary_fallback(self) -> str:
        prev_id = self._previous_chapter_id()
        if not prev_id:
            return ""
        prev_text = self.store.read_chapter_text(self.project_dir, self.project, prev_id)  # type: ignore[arg-type]
        prev_text = prev_text.strip()
        if not prev_text:
            return ""
        # fallback: first 300 chars
        return (prev_text[:300] + ("…" if len(prev_text) > 300 else "")).strip()

    def _backtrack(self) -> None:
        if not self._ensure_project_open() or not self.current_chapter_id:
            return
        prev_id = self._previous_chapter_id()
        if not prev_id:
            QMessageBox.information(self, "回溯阅读", "暂无上一章可回溯。")
            return
        meta = self.project.chapters[prev_id]
        prev_text = self.store.read_chapter_text(self.project_dir, self.project, prev_id)  # type: ignore[arg-type]
        if not prev_text.strip():
            QMessageBox.information(self, "回溯阅读", "上一章内容为空。")
            return

        summary = "（未配置AI）" if not load_ai_context() else ""
        self._backtrack_dialog = BacktrackDialog(meta.title, prev_text, summary_text=summary, parent=self)
        self._backtrack_dialog.setModal(True)
        if load_ai_context():
            self._backtrack_dialog.set_summary_loading()
        self._backtrack_dialog.show()

        if not load_ai_context():
            self._backtrack_dialog.set_summary(self._previous_chapter_summary_fallback())
            return

        def work() -> str:
            return ai_summarize(prev_text)

        def ok(s: str) -> None:
            if self._backtrack_dialog:
                self._backtrack_dialog.set_summary(s.strip())

        def err(e: Exception) -> None:
            if self._backtrack_dialog:
                self._backtrack_dialog.set_summary(self._previous_chapter_summary_fallback() or f"摘要生成失败：{e}")

        BackgroundTask(func=work, on_success=ok, on_error=err).start()

