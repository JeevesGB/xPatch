from pathlib import Path
from PyQt6.QtCore import QObject, QProcess, pyqtSignal

class XDeltaRunner(QObject):
    output_received = pyqtSignal(str)
    finished = pyqtSignal(int)

    def __init__(self, executable: Path):
        super().__init__()
        self.process = QProcess(self)
        self.process.setProgram(str(executable))

        self.process.readyReadStandardOutput.connect(self._handle_stdout)
        self.process.readyReadStandardError.connect(self._handle_stderr)
        self.process.finished.connect(self._finished)

    def run(self, args: list[str]) -> None:
        self.process.setArguments(args)
        self.process.start()

    def is_running(self) -> bool:
        return self.process.state() == QProcess.ProcessState.Running

    def _handle_stdout(self):
        self.output_received.emit(
            bytes(self.process.readAllStandardOutput()).decode()
        )

    def _handle_stderr(self):
        self.output_received.emit(
            bytes(self.process.readAllStandardError()).decode()
        )

    def _finished(self, exitCode: int, _):
        self.finished.emit(exitCode)