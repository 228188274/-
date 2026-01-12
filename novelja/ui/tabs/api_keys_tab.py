from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QFormLayout,
    QLineEdit,
    QPushButton,
    QHBoxLayout,
    QComboBox,
    QMessageBox,
)

from novelja.core.ai.providers import AiError, test_connection
from novelja.core.security import AiSettings, load_ai_settings, load_api_key, save_ai_settings, save_api_key
from novelja.ui.async_worker import BackgroundTask


class ApiKeysTab(QWidget):
    """
    API密钥与AI默认设置：
    - API Key：优先存入系统Keyring；否则退回本地配置文件（不会进入项目导出包）
    - 支持 DeepSeek / 智谱的连通性测试（发送简单对话请求）
    """

    def __init__(self) -> None:
        super().__init__()

        root = QVBoxLayout(self)
        root.addWidget(QLabel("配置 DeepSeek / 智谱 API 密钥（本地存储）"))

        form = QFormLayout()
        self.provider = QComboBox()
        self.provider.addItems(["deepseek", "zhipu"])
        form.addRow("提供方", self.provider)

        self.base_url = QLineEdit()
        self.base_url.setPlaceholderText("可选：自定义API地址（留空使用默认）")
        form.addRow("Base URL", self.base_url)

        self.model = QLineEdit()
        self.model.setPlaceholderText("可选：模型名（例如 deepseek-chat / glm-4-flash）")
        form.addRow("默认模型", self.model)

        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.Password)
        self.api_key.setPlaceholderText("粘贴 API Key（不会进入项目导出包）")
        form.addRow("API Key", self.api_key)

        root.addLayout(form)

        row = QHBoxLayout()
        self.btn_save = QPushButton("保存")
        self.btn_test = QPushButton("测试连通性")
        self.btn_save.setProperty("variant", "primary")
        row.addWidget(self.btn_save)
        row.addWidget(self.btn_test)
        row.addStretch(1)
        root.addLayout(row)

        root.addStretch(1)

        self.btn_save.clicked.connect(self._on_save)
        self.btn_test.clicked.connect(self._on_test)
        self.provider.currentTextChanged.connect(self._load_for_provider)

        self._load_initial()

    def _load_initial(self) -> None:
        s = load_ai_settings()
        idx = max(0, self.provider.findText(s.provider))
        self.provider.setCurrentIndex(idx)
        self.base_url.setText(s.base_url)
        self.model.setText(s.model)
        self._load_for_provider(self.provider.currentText())

    def _load_for_provider(self, provider: str) -> None:
        # 不直接回显密钥（只提示是否已配置）
        key = load_api_key(provider)
        self.api_key.setText("")
        if key:
            self.api_key.setPlaceholderText("已配置（如需更新，请重新粘贴）")
        else:
            self.api_key.setPlaceholderText("粘贴 API Key（不会进入项目导出包）")

    def _on_save(self) -> None:
        provider = self.provider.currentText().strip()
        base_url = self.base_url.text().strip()
        model = self.model.text().strip()

        if self.api_key.text().strip():
            save_api_key(provider, self.api_key.text().strip())

        save_ai_settings(AiSettings(provider=provider, model=model, base_url=base_url))
        QMessageBox.information(self, "已保存", "AI设置已保存。")

    def _on_test(self) -> None:
        provider = self.provider.currentText().strip()
        base_url = self.base_url.text().strip()
        model = self.model.text().strip()
        key = self.api_key.text().strip() or load_api_key(provider)

        if not key:
            QMessageBox.warning(self, "无法测试", "未配置 API Key，请先保存或粘贴后再测试。")
            return

        self.btn_test.setEnabled(False)
        self.btn_save.setEnabled(False)
        self.btn_test.setText("测试中…")

        def work() -> str:
            return test_connection(provider=provider, api_key=key, base_url=base_url, model=model)

        def ok(result: str) -> None:
            self.btn_test.setEnabled(True)
            self.btn_save.setEnabled(True)
            self.btn_test.setText("测试连通性")
            QMessageBox.information(self, "测试成功", f"模型回复：{result}")

        def err(e: Exception) -> None:
            self.btn_test.setEnabled(True)
            self.btn_save.setEnabled(True)
            self.btn_test.setText("测试连通性")
            if isinstance(e, AiError):
                QMessageBox.warning(self, "测试失败", f"{e.kind}: {e}")
            else:
                QMessageBox.warning(self, "测试失败", str(e))

        BackgroundTask(func=work, on_success=ok, on_error=err).start()

