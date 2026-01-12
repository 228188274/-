from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Generic, TypeVar

from PySide6.QtCore import QObject, QThread, Signal

T = TypeVar("T")


class _WorkerSignals(QObject):
    finished = Signal(object)
    failed = Signal(Exception)


@dataclass
class BackgroundTask(Generic[T]):
    func: Callable[[], T]
    on_success: Callable[[T], None]
    on_error: Callable[[Exception], None]

    def start(self) -> None:
        # Keep references on self to prevent premature GC.
        self._thread = QThread()
        self._signals = _WorkerSignals()

        class Runner(QObject):
            def run(self) -> None:
                try:
                    result = self_outer.func()
                    self_outer._signals.finished.emit(result)
                except Exception as e:  # noqa: BLE001
                    self_outer._signals.failed.emit(e)

        self_outer = self
        runner = Runner()
        runner.moveToThread(self._thread)

        def cleanup() -> None:
            self_outer._thread.quit()
            self_outer._thread.wait(2000)
            runner.deleteLater()
            self_outer._signals.deleteLater()
            self_outer._thread.deleteLater()
            # break ref cycles
            self_outer._signals = None  # type: ignore[assignment]
            self_outer._thread = None  # type: ignore[assignment]

        self._signals.finished.connect(lambda r: (self.on_success(r), cleanup()))
        self._signals.failed.connect(lambda e: (self.on_error(e), cleanup()))
        self._thread.started.connect(runner.run)
        self._thread.start()

