from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from novelja.ui.main_window import MainWindow
from novelja.ui.app_state import get_app_state


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("小说佳")
    app.setOrganizationName("novelja")
    # Initialize global app state (cross-tab project sharing)
    get_app_state()

    window = MainWindow()
    window.show()
    return app.exec()

