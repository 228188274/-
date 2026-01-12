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
        self._action: str | None = None  # replace | insert | copy | None

        root = QVBoxLayout(self)
        root.addWidget(QLabel("对比原文与润色结果，选择应用方式："))

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
        self.btn_apply_replace = QPushButton("替换")
        self.btn_apply_replace.setProperty("variant", "primary")
        self.btn_apply_insert = QPushButton("插入到光标处")
        self.btn_copy = QPushButton("复制润色结果")
        self.btn_cancel = QPushButton("取消")
        btns.addWidget(self.btn_apply_replace)
        btns.addWidget(self.btn_apply_insert)
        btns.addWidget(self.btn_copy)
        btns.addWidget(self.btn_cancel)
        root.addLayout(btns)

        self.btn_apply_replace.clicked.connect(self._choose_replace)
        self.btn_apply_insert.clicked.connect(self._choose_insert)
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_copy.clicked.connect(self._copy)

    def chosen_action(self) -> str | None:
        return self._action

    def _choose_replace(self) -> None:
        self._action = "replace"
        self.accept()

    def _choose_insert(self) -> None:
        self._action = "insert"
        self.accept()

    def _copy(self) -> None:
        cb = self.clipboard()
        if cb:
            cb.setText(self.polished_view.toPlainText(), mode=cb.Clipboard)
        self._action = "copy"

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

