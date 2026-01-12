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
        thread = QThread()
        signals = _WorkerSignals()

        class Runner(QObject):
            def run(self) -> None:
                try:
                    result = self_outer.func()
                    signals.finished.emit(result)
                except Exception as e:  # noqa: BLE001
                    signals.failed.emit(e)

        self_outer = self
        runner = Runner()
        runner.moveToThread(thread)

        def cleanup() -> None:
            thread.quit()
            thread.wait(2000)
            runner.deleteLater()
            signals.deleteLater()
            thread.deleteLater()

        signals.finished.connect(lambda r: (self.on_success(r), cleanup()))
        signals.failed.connect(lambda e: (self.on_error(e), cleanup()))
        thread.started.connect(runner.run)
        thread.start()

