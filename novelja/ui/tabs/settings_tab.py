from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget

from novelja.ui.tabs.api_keys_tab import ApiKeysTab


class SettingsTab(QWidget):
    """
    Settings container tab. Keeps main navigation clean.
    """

    def __init__(self) -> None:
        super().__init__()
        root = QVBoxLayout(self)
        root.addWidget(QLabel("设置"))

        inner = QTabWidget()
        inner.setDocumentMode(True)
        inner.addTab(ApiKeysTab(), "API密钥")
        root.addWidget(inner, 1)

