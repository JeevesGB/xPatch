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
        self.output_received.emit(f"Running: xdelta3 {' '.join(args)}\n")
        self.process.start()

    def is_running(self) -> bool:
        return self.process.state() == QProcess.ProcessState.Running

    def _handle_stdout(self):
        output = bytes(self.process.readAllStandardOutput()).decode('utf-8', errors='replace').strip()
        if output:
            self.output_received.emit(output)

    def _handle_stderr(self):
        error = bytes(self.process.readAllStandardError()).decode('utf-8', errors='replace').strip()
        if error:
            self.output_received.emit(f"ERROR: {error}")

    def _finished(self, exitCode: int, _):
        if exitCode == 0:
            self.output_received.emit("Process finished successfully.")
        else:
            self.output_received.emit(f"Process failed with exit code: {exitCode}")
        self.finished.emit(exitCode)