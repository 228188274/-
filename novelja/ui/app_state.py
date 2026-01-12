from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from novelja.core.models import Project
from novelja.core.security import add_recent_project, set_last_project


@dataclass
class CurrentProject:
    folder: Path
    project: Project


class AppState(QObject):
    """
    Global UI state for cross-tab coordination.

    - Holds the current opened project folder + loaded project metadata.
    - Emits signal when project changes so other tabs can refresh.
    """

    projectChanged = Signal(object)  # CurrentProject | None

    def __init__(self) -> None:
        super().__init__()
        self._current: CurrentProject | None = None

    def current_project(self) -> CurrentProject | None:
        return self._current

    def set_current_project(self, folder: Path, project: Project) -> None:
        self._current = CurrentProject(folder=folder, project=project)
        add_recent_project(str(folder))
        set_last_project(str(folder))
        self.projectChanged.emit(self._current)

    def clear_project(self) -> None:
        self._current = None
        self.projectChanged.emit(None)


def get_app_state() -> AppState:
    """
    Singleton stored on QApplication to avoid module-global lifetime issues.
    """
    app = QApplication.instance()
    if app is None:
        # Fallback (shouldn't happen in real app runtime)
        return AppState()

    # IMPORTANT: Use a Python attribute to keep a strong reference.
    # Qt dynamic properties may not retain a Python object strongly,
    # which can lead to "Signal source has been deleted".
    state = getattr(app, "_novelja_app_state", None)
    if isinstance(state, AppState):
        return state

    state = AppState()
    setattr(app, "_novelja_app_state", state)
    return state

