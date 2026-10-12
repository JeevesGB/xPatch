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
        self.process.finished.connect(self._on_finished)

    def run(self, args: list[str]) -> None:
        self.process.setArguments(args)
        self.output_received.emit(f"Running: xdelta3 {' '.join(args)}")
        self.process.start()

    def is_running(self) -> bool:
        return self.process.state() == QProcess.ProcessState.Running

    def _handle_stdout(self) -> None:
        raw = bytes(self.process.readAllStandardOutput()).decode(
            "utf-8", errors="replace"
        )
        for line in raw.splitlines():
            line = line.strip()
            if line:
                self.output_received.emit(line)

    def _handle_stderr(self) -> None:
        raw = bytes(self.process.readAllStandardError()).decode(
            "utf-8", errors="replace"
        )
        for line in raw.splitlines():
            line = line.strip()
            if line:
                # xdelta often writes status to stderr even on success
                self.output_received.emit(line)

    def _on_finished(self, exit_code: int, _status) -> None:
        if exit_code == 0:
            self.output_received.emit("Process finished successfully.")
        else:
            self.output_received.emit(f"Process failed with exit code: {exit_code}")
        self.finished.emit(exit_code)
