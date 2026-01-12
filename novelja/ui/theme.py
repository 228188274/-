from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication


def apply_theme(app: QApplication) -> None:
    """
    Apply a clean, modern light theme.
    Notes:
    - We intentionally keep this lightweight (QPalette + QSS) for cross-platform stability.
    - Widgets can opt-in to variants via dynamic properties, e.g. button.setProperty("variant","primary").
    """

    # Typography
    font = QFont()
    font.setPointSize(10)
    # Prefer CJK-capable fonts; fall back to system defaults.
    font.setFamilies(
        [
            "Noto Sans CJK SC",
            "Noto Sans SC",
            "Source Han Sans SC",
            "Microsoft YaHei",
            "PingFang SC",
            "Heiti SC",
            "DejaVu Sans",
            "Sans Serif",
        ]
    )
    app.setFont(font)

    # Palette (base colors)
    palette = QPalette()
    c_window = QColor("#F7F8FA")
    c_base = QColor("#FFFFFF")
    c_text = QColor("#111827")
    c_muted = QColor("#6B7280")
    c_border = QColor("#E5E7EB")
    c_primary = QColor("#2563EB")
    c_primary_hover = QColor("#1D4ED8")
    c_primary_pressed = QColor("#1E40AF")
    c_focus = QColor("#93C5FD")

    palette.setColor(QPalette.Window, c_window)
    palette.setColor(QPalette.Base, c_base)
    palette.setColor(QPalette.AlternateBase, QColor("#F3F4F6"))
    palette.setColor(QPalette.Text, c_text)
    palette.setColor(QPalette.WindowText, c_text)
    palette.setColor(QPalette.Button, c_base)
    palette.setColor(QPalette.ButtonText, c_text)
    palette.setColor(QPalette.Highlight, c_primary)
    palette.setColor(QPalette.HighlightedText, QColor("#FFFFFF"))
    palette.setColor(QPalette.PlaceholderText, c_muted)
    app.setPalette(palette)

    # QSS
    app.setStyleSheet(
        f"""
        /* Global */
        QWidget {{
            color: {c_text.name()};
            font-size: 10pt;
        }}

        QMainWindow {{
            background: {c_window.name()};
        }}

        QMenuBar {{
            background: {c_base.name()};
            border-bottom: 1px solid {c_border.name()};
        }}
        QMenuBar::item {{
            padding: 6px 10px;
            margin: 2px 2px;
            border-radius: 6px;
        }}
        QMenuBar::item:selected {{
            background: #EFF6FF;
        }}

        QMenu {{
            background: {c_base.name()};
            border: 1px solid {c_border.name()};
            padding: 6px;
        }}
        QMenu::item {{
            padding: 6px 10px;
            border-radius: 6px;
        }}
        QMenu::item:selected {{
            background: #EFF6FF;
        }}

        QStatusBar {{
            background: {c_base.name()};
            border-top: 1px solid {c_border.name()};
        }}

        /* Inputs */
        QLineEdit, QPlainTextEdit, QTextEdit, QComboBox {{
            background: {c_base.name()};
            border: 1px solid {c_border.name()};
            border-radius: 8px;
            padding: 8px 10px;
            selection-background-color: {c_primary.name()};
        }}
        QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QComboBox:focus {{
            border: 1px solid {c_primary.name()};
        }}

        QPlainTextEdit {{
            line-height: 1.4;
        }}

        /* Buttons */
        QPushButton {{
            background: {c_base.name()};
            border: 1px solid {c_border.name()};
            border-radius: 10px;
            padding: 8px 12px;
        }}
        QPushButton:hover {{
            background: #F9FAFB;
        }}
        QPushButton:pressed {{
            background: #F3F4F6;
        }}
        QPushButton:disabled {{
            color: {c_muted.name()};
            background: #F3F4F6;
            border-color: {c_border.name()};
        }}

        QPushButton[variant="primary"] {{
            background: {c_primary.name()};
            color: #FFFFFF;
            border: 1px solid {c_primary.name()};
            font-weight: 600;
        }}
        QPushButton[variant="primary"]:hover {{
            background: {c_primary_hover.name()};
            border-color: {c_primary_hover.name()};
        }}
        QPushButton[variant="primary"]:pressed {{
            background: {c_primary_pressed.name()};
            border-color: {c_primary_pressed.name()};
        }}
        QPushButton[variant="danger"] {{
            background: #DC2626;
            color: #FFFFFF;
            border: 1px solid #DC2626;
        }}
        QPushButton[variant="danger"]:hover {{
            background: #B91C1C;
            border-color: #B91C1C;
        }}

        /* Lists */
        QListWidget {{
            background: {c_base.name()};
            border: 1px solid {c_border.name()};
            border-radius: 10px;
            padding: 6px;
        }}
        QListWidget::item {{
            padding: 8px 10px;
            border-radius: 8px;
        }}
        QListWidget::item:selected {{
            background: #EFF6FF;
            border: 1px solid #BFDBFE;
        }}

        /* Tabs */
        QTabWidget::pane {{
            border: 1px solid {c_border.name()};
            border-radius: 12px;
            top: -1px;
            background: {c_base.name()};
        }}
        QTabBar::tab {{
            background: transparent;
            padding: 10px 14px;
            margin: 6px 4px 0px 4px;
            border-top-left-radius: 10px;
            border-top-right-radius: 10px;
            color: {c_muted.name()};
        }}
        QTabBar::tab:selected {{
            color: {c_text.name()};
            background: {c_base.name()};
            border: 1px solid {c_border.name()};
            border-bottom: 1px solid {c_base.name()};
        }}
        QTabBar::tab:hover {{
            background: #F9FAFB;
        }}

        /* Splitter */
        QSplitter::handle {{
            background: transparent;
        }}
        QSplitter::handle:horizontal {{
            width: 10px;
        }}
        QSplitter::handle:vertical {{
            height: 10px;
        }}
        """
    )

