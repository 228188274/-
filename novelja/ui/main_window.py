from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QLabel,
    QMessageBox,
)

from pathlib import Path

from novelja.core.security import load_last_project, load_recent_projects
from novelja.ui.app_state import CurrentProject, get_app_state
from novelja.ui.tabs.create_tab import CreateTab
from novelja.ui.tabs.api_keys_tab import ApiKeysTab
from novelja.ui.tabs.agent_tab import AgentTab


class PlaceholderTab(QWidget):
    def __init__(self, title: str) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        label = QLabel(f"{title}：开发中")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("小说佳 - AI辅助小说创作工具")
        self.resize(1200, 800)

        self.tabs = QTabWidget()
        tabs = self.tabs
        tabs.setDocumentMode(True)

        # 参考原型的导航结构（MVP优先实现：开始创作、API密钥、智能体模式）
        tabs.addTab(PlaceholderTab("智能对话"), "智能对话")
        tabs.addTab(PlaceholderTab("智能体管理"), "智能体管理")
        tabs.addTab(PlaceholderTab("大纲创作"), "大纲创作")
        tabs.addTab(PlaceholderTab("角色管理"), "角色管理")
        tabs.addTab(PlaceholderTab("章节编辑"), "章节编辑")

        self.create_tab = CreateTab()
        tabs.addTab(self.create_tab, "开始创作")
        tabs.addTab(PlaceholderTab("文件管理"), "文件管理")
        tabs.addTab(PlaceholderTab("文本润色"), "文本润色")

        tabs.addTab(ApiKeysTab(), "API密钥")
        tabs.addTab(AgentTab(), "智能体模式")

        self.setCentralWidget(tabs)

        self._init_menu()
        self._init_status_bar()
        self._auto_open_last_project()

    def _init_menu(self) -> None:
        bar = self.menuBar()
        menu_file = bar.addMenu("文件")

        act_new = QAction("新建作品", self)
        act_new.setShortcut("Ctrl+N")
        act_new.triggered.connect(lambda: (self.tabs.setCurrentWidget(self.create_tab), self.create_tab.menu_new_project()))

        act_open = QAction("打开作品", self)
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(lambda: (self.tabs.setCurrentWidget(self.create_tab), self.create_tab.menu_open_project()))

        act_import = QAction("导入…", self)
        act_import.setShortcut("Ctrl+I")
        act_import.triggered.connect(lambda: (self.tabs.setCurrentWidget(self.create_tab), self.create_tab.menu_import()))

        act_export = QAction("导出…", self)
        act_export.setShortcut("Ctrl+E")
        act_export.triggered.connect(lambda: (self.tabs.setCurrentWidget(self.create_tab), self.create_tab.menu_export()))

        act_quit = QAction("退出", self)
        act_quit.setShortcut("Ctrl+Q")
        act_quit.triggered.connect(self.close)

        menu_file.addAction(act_new)
        menu_file.addAction(act_open)
        menu_recent = menu_file.addMenu("最近打开")
        menu_recent.aboutToShow.connect(lambda: self._populate_recent(menu_recent))
        menu_file.addSeparator()
        menu_file.addAction(act_import)
        menu_file.addAction(act_export)
        menu_file.addSeparator()
        menu_file.addAction(act_quit)

        menu_help = bar.addMenu("帮助")
        act_about = QAction("关于", self)
        act_about.triggered.connect(self._about)
        menu_help.addAction(act_about)

    def _populate_recent(self, menu_recent) -> None:
        menu_recent.clear()
        items = load_recent_projects()
        if not items:
            disabled = QAction("（暂无）", self)
            disabled.setEnabled(False)
            menu_recent.addAction(disabled)
            return
        any_valid = False
        for p in items:
            folder = Path(p)
            if not (folder.exists() and (folder / "project.json").exists()):
                continue
            any_valid = True
            act = QAction(p, self)
            act.triggered.connect(lambda checked=False, path=p: self._open_recent(path))
            menu_recent.addAction(act)
        if not any_valid:
            disabled = QAction("（暂无可用项目）", self)
            disabled.setEnabled(False)
            menu_recent.addAction(disabled)

    def _open_recent(self, path: str) -> None:
        # Delegate to CreateTab: open project directory (no extra prompts)
        self.tabs.setCurrentWidget(self.create_tab)
        self.create_tab.open_project_path(path)

    def _auto_open_last_project(self) -> None:
        """
        Startup quality-of-life: if last project exists, open it silently.
        """
        p = load_last_project()
        if not p:
            return
        self.tabs.setCurrentWidget(self.create_tab)
        self.create_tab.open_project_path(p, silent=True)

    def _about(self) -> None:
        QMessageBox.information(self, "关于 小说佳", "小说佳（开发版）：本地小说创作 + AI辅助（DeepSeek/智谱）")

    def _init_status_bar(self) -> None:
        self.statusBar().showMessage("未打开作品")
        get_app_state().projectChanged.connect(self._on_project_changed)
        current = get_app_state().current_project()
        if current:
            self._on_project_changed(current)

    def _on_project_changed(self, current: object) -> None:
        if current is None:
            self.statusBar().showMessage("未打开作品")
            return
        if not isinstance(current, CurrentProject):
            return
        proj = current.project
        autosave = getattr(getattr(proj, "settings", None), "autosaveEnabled", True)
        autosave_s = "开" if autosave else "关"
        self.statusBar().showMessage(f"作品：{proj.title}    位置：{current.folder}    自动保存：{autosave_s}")

