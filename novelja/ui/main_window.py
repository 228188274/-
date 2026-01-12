from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QLabel,
)

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

        tabs = QTabWidget()
        tabs.setDocumentMode(True)

        # 参考原型的导航结构（MVP优先实现：开始创作、API密钥、智能体模式）
        tabs.addTab(PlaceholderTab("智能对话"), "智能对话")
        tabs.addTab(PlaceholderTab("智能体管理"), "智能体管理")
        tabs.addTab(PlaceholderTab("大纲创作"), "大纲创作")
        tabs.addTab(PlaceholderTab("角色管理"), "角色管理")
        tabs.addTab(PlaceholderTab("章节编辑"), "章节编辑")

        tabs.addTab(CreateTab(), "开始创作")
        tabs.addTab(PlaceholderTab("文件管理"), "文件管理")
        tabs.addTab(PlaceholderTab("文本润色"), "文本润色")

        tabs.addTab(ApiKeysTab(), "API密钥")
        tabs.addTab(AgentTab(), "智能体模式")

        self.setCentralWidget(tabs)

