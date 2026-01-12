from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
)


class PolishCompareDialog(QDialog):
    def __init__(self, original: str, polished: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("AI润色对比")
        self.resize(1000, 700)

        root = QVBoxLayout(self)
        root.addWidget(QLabel("对比原文与润色结果，确认后再应用："))

        row = QHBoxLayout()

        left_box = QVBoxLayout()
        left_box.addWidget(QLabel("原文"))
        self.original_view = QPlainTextEdit()
        self.original_view.setPlainText(original)
        self.original_view.setReadOnly(True)
        left_box.addWidget(self.original_view, 1)

        right_box = QVBoxLayout()
        right_box.addWidget(QLabel("润色后"))
        self.polished_view = QPlainTextEdit()
        self.polished_view.setPlainText(polished)
        self.polished_view.setReadOnly(True)
        right_box.addWidget(self.polished_view, 1)

        row.addLayout(left_box, 1)
        row.addLayout(right_box, 1)
        root.addLayout(row, 1)

        btns = QHBoxLayout()
        btns.addStretch(1)
        self.btn_apply_replace = QPushButton("替换原文")
        self.btn_copy = QPushButton("复制润色结果")
        self.btn_cancel = QPushButton("取消")
        btns.addWidget(self.btn_apply_replace)
        btns.addWidget(self.btn_copy)
        btns.addWidget(self.btn_cancel)
        root.addLayout(btns)

        self.btn_apply_replace.clicked.connect(self.accept)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_copy.clicked.connect(self._copy)

    def _copy(self) -> None:
        cb = self.clipboard()
        if cb:
            cb.setText(self.polished_view.toPlainText(), mode=cb.Clipboard)

    @staticmethod
    def clipboard():
        # QApplication.clipboard is only available when app is running; imported lazily.
        try:
            from PySide6.QtWidgets import QApplication

            return QApplication.clipboard()
        except Exception:
            return None

    def polished_text(self) -> str:
        return self.polished_view.toPlainText()

