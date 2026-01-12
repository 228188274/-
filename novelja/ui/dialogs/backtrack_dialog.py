from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)


class BacktrackDialog(QDialog):
    def __init__(self, chapter_title: str, chapter_text: str, summary_text: str = "", parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("回溯阅读")
        self.resize(900, 650)

        root = QVBoxLayout(self)
        root.addWidget(QLabel(f"回溯：{chapter_title}"))

        cols = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("原文（只读）"))
        self.text_view = QPlainTextEdit()
        self.text_view.setReadOnly(True)
        self.text_view.setPlainText(chapter_text)
        left.addWidget(self.text_view, 1)

        right = QVBoxLayout()
        self.summary_label = QLabel("摘要（可复制）")
        right.addWidget(self.summary_label)
        self.summary_view = QPlainTextEdit()
        self.summary_view.setPlainText(summary_text)
        right.addWidget(self.summary_view, 1)

        cols.addLayout(left, 2)
        cols.addLayout(right, 1)
        root.addLayout(cols, 1)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.btn_copy = QPushButton("复制摘要")
        self.btn_copy.setProperty("variant", "primary")
        self.btn_close = QPushButton("关闭")
        btns.addWidget(self.btn_copy)
        btns.addWidget(self.btn_close)
        root.addLayout(btns)

        self.btn_close.clicked.connect(self.accept)
        self.btn_copy.clicked.connect(self._copy_summary)

    def set_summary_loading(self) -> None:
        self.summary_label.setText("摘要（生成中…）")
        self.summary_view.setPlainText("生成中…")

    def set_summary(self, text: str) -> None:
        self.summary_label.setText("摘要（可复制）")
        self.summary_view.setPlainText(text)

    def _copy_summary(self) -> None:
        try:
            from PySide6.QtWidgets import QApplication

            cb = QApplication.clipboard()
            cb.setText(self.summary_view.toPlainText(), mode=cb.Clipboard)
        except Exception:
            pass

