from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
)


class ChangeDetailDialog(QDialog):
    def __init__(
        self,
        *,
        title: str,
        reason: str,
        kind: str,
        before_text: str,
        after_text: str,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("改动详情")
        self.resize(1000, 700)

        root = QVBoxLayout(self)
        hdr = QLabel(title)
        hdr.setAlignment(Qt.AlignLeft)
        root.addWidget(hdr)
        root.addWidget(QLabel(f"类型：{kind}"))
        root.addWidget(QLabel(f"原因：{reason}"))

        row = QHBoxLayout()
        left = QVBoxLayout()
        left.addWidget(QLabel("Before"))
        before = QPlainTextEdit()
        before.setReadOnly(True)
        before.setPlainText(before_text or "")
        left.addWidget(before, 1)

        right = QVBoxLayout()
        right.addWidget(QLabel("After"))
        after = QPlainTextEdit()
        after.setReadOnly(True)
        after.setPlainText(after_text or "")
        right.addWidget(after, 1)

        row.addLayout(left, 1)
        row.addLayout(right, 1)
        root.addLayout(row, 1)

        btns = QHBoxLayout()
        btns.addStretch(1)
        close = QPushButton("关闭")
        btns.addWidget(close)
        root.addLayout(btns)
        close.clicked.connect(self.accept)

