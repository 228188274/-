from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QApplication,
)

from novelja.ui.tabs.api_keys_tab import ApiKeysTab
from novelja.core.security import load_default_autosave, load_ui_theme, save_default_autosave, save_ui_theme
from novelja.ui.theme import apply_theme


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
        inner.addTab(self._build_general(), "常规")
        inner.addTab(ApiKeysTab(), "API密钥")
        root.addWidget(inner, 1)

    def _build_general(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        box_ui = QGroupBox("界面")
        form_ui = QFormLayout(box_ui)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["system", "light", "dark"])
        self.theme_combo.setCurrentText(load_ui_theme())
        form_ui.addRow("主题", self.theme_combo)
        layout.addWidget(box_ui)

        box_proj = QGroupBox("新建作品默认设置")
        form_proj = QFormLayout(box_proj)
        enabled, seconds = load_default_autosave()
        self.autosave_enabled = QCheckBox("启用自动保存")
        self.autosave_enabled.setChecked(enabled)
        self.autosave_seconds = QSpinBox()
        self.autosave_seconds.setRange(2, 600)
        self.autosave_seconds.setValue(seconds)
        self.autosave_seconds.setSuffix(" 秒")
        form_proj.addRow("自动保存", self.autosave_enabled)
        form_proj.addRow("间隔", self.autosave_seconds)
        layout.addWidget(box_proj)

        self.btn_save = QPushButton("保存设置")
        self.btn_save.setProperty("variant", "primary")
        layout.addWidget(self.btn_save)
        layout.addStretch(1)

        self.btn_save.clicked.connect(self._save_general)
        self.theme_combo.currentTextChanged.connect(self._apply_theme_live)

        return w

    def _apply_theme_live(self) -> None:
        # Apply immediately so the user can preview.
        app = QApplication.instance()
        if app:
            apply_theme(app, self.theme_combo.currentText())

    def _save_general(self) -> None:
        save_ui_theme(self.theme_combo.currentText())
        save_default_autosave(self.autosave_enabled.isChecked(), int(self.autosave_seconds.value()))
