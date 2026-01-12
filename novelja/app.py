from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from novelja.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("小说佳")
    app.setOrganizationName("novelja")

    window = MainWindow()
    window.show()
    return app.exec()

