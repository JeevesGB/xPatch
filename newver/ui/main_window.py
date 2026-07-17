from pathlib import Path
from PyQt6.QtWidgets import *
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon

from services.xdelta_runner import XDeltaRunner
from utils.paths import resource_path, find_xdelta
from utils.checksum import calculate_hash
from utils.files import copy_cue_file

VERSION = "0.1.25"
UPDATE_URL = "https://github.com/JeevesGB/xPatch"
theme = "ui/theme.qss"
icon_path = resource_path("ico.ico")

class XPatchWindow(QWidget):

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"xPatch v{VERSION}")
        self.setWindowIcon(QIcon(str(icon_path)))
        self._load_stylesheet()
        self.setMinimumSize(760, 620)
        self.setAcceptDrops(True)

        self.mode = "create"
        self.output_path: Path | None = None
        self.source_size = 0

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        grid = QGridLayout()

        # Mode buttons
        self.create_btn = QPushButton("Create Patch")
        self.apply_btn = QPushButton("Apply Patch")
        self.create_btn.clicked.connect(lambda: self._set_mode("create"))
        self.create_btn.setObjectName("createPatchButton")
        self.apply_btn.setObjectName("applyPatchButton")
        self.create_btn.setCheckable(True)
        self.apply_btn.setCheckable(True)
        self.create_btn.clicked.connect(lambda: self._set_mode("create"))
        self.apply_btn.clicked.connect(lambda: self._set_mode("apply"))
        

        self.help_btn = QPushButton("Help")
        self.about_btn = QPushButton("Version")
        self.help_btn.setFixedWidth(55)
        self.help_btn.clicked.connect(self.show_help)
        self.about_btn.clicked.connect(self.show_about)

        mode_row = QHBoxLayout()
        mode_row.addWidget(self.create_btn)
        mode_row.addWidget(self.apply_btn)
        mode_row.addStretch()
        mode_row.addWidget(self.help_btn)
        mode_row.addWidget(self.about_btn)

        grid.addLayout(mode_row, 0, 0, 1, 3)

        self.orig_edit = QLineEdit()
        self.mod_edit = QLineEdit()
        self.patch_edit = QLineEdit()
        self.output_edit = QLineEdit()

        fields = [
            ("Original BIN:", self.orig_edit),
            ("Modified BIN:", self.mod_edit),
            ("xDelta Patch:", self.patch_edit),
            ("Output BIN:", self.output_edit),
        ]

        for row, (label, edit) in enumerate(fields, start=1):
            btn = QPushButton("Browse")
            btn.clicked.connect(lambda _, e=edit: self._browse(e))
            grid.addWidget(QLabel(label), row, 0)
            grid.addWidget(edit, row, 1)
            grid.addWidget(btn, row, 2)

        self.action_btn = QPushButton("Create xDelta Patch")
        self.action_btn.clicked.connect(self._run)
        grid.addWidget(self.action_btn, 5, 0, 1, 3)

        layout.addLayout(grid)

        self.progress = QProgressBar()
        layout.addWidget(self.progress)
        layout.addWidget(QLabel("Console Output:"))
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        layout.addWidget(self.console)

        export_btn = QPushButton("Export Log")
        export_btn.clicked.connect(self._export_log)
        layout.addWidget(export_btn)

        self._set_mode("create")

    def _load_stylesheet(self) -> None:
        theme_path = resource_path(theme)
        
        print(f"Looking for theme at: {theme_path}")  # ← Add this for debugging
        
        if theme_path.exists():
            try:
                stylesheet = theme_path.read_text(encoding="utf-8")
                self.setStyleSheet(stylesheet)
                print("✓ Theme loaded successfully")
            except Exception as e:
                print(f"Failed to load stylesheet: {e}")
        else:
            print(f"✗ Stylesheet not found: {theme_path}")

    def _set_mode(self, mode: str):
        self.mode = mode
        is_create = mode == "create"
        
        self.create_btn.setChecked(is_create)
        self.apply_btn.setChecked(not is_create)
        
        self.mod_edit.setEnabled(is_create)
        self.output_edit.setEnabled(not is_create)
        self.action_btn.setText(
            "Create xDelta Patch" if is_create else "Apply Patch"
        )

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if not self.orig_edit.text():
                self.orig_edit.setText(str(path))
            elif self.mode == "create" and not self.mod_edit.text():
                self.mod_edit.setText(str(path))
            elif not self.patch_edit.text():
                self.patch_edit.setText(str(path))

    def _browse(self, edit: QLineEdit):
        if edit == self.patch_edit and self.mode == "create":
            path, _ = QFileDialog.getSaveFileName(self, "Save Patch", "", "*.xdelta")
        elif edit == self.output_edit:
            path, _ = QFileDialog.getSaveFileName(self, "Save Output", "", "*.bin")
        else:
            path, _ = QFileDialog.getOpenFileName(self)

        if path:
            edit.setText(path)

    def _validate(self) -> bool:
        orig = Path(self.orig_edit.text())
        if not orig.exists():
            QMessageBox.critical(self, "Error", "Original file missing.")
            return False

        if self.mode == "create":
            mod = Path(self.mod_edit.text())
            if not mod.exists():
                QMessageBox.critical(self, "Error", "Modified file missing.")
                return False
            if orig == mod:
                QMessageBox.warning(self, "Error", "Original and Modified cannot match.")
                return False
        return True

    def _run(self):
        if not self._validate():
            return

        xdelta = find_xdelta()
        if not xdelta:
            QMessageBox.critical(self, "Error", "xdelta3 not found.")
            return

        self.runner = XDeltaRunner(xdelta)
        if self.runner.is_running():
            return

        orig = Path(self.orig_edit.text())
        patch = Path(self.patch_edit.text())

        self.console.clear()
        self.progress.setRange(0, 0)

        if self.mode == "create":
            mod = Path(self.mod_edit.text())
            args = ["-e", "-s", str(orig), str(mod), str(patch)]
            self.console.appendPlainText(f"Creating xDelta patch...")
            self.console.appendPlainText(f"Original : {orig.name} ({orig.stat().st_size:,} bytes)")
            self.console.appendPlainText(f"Modified : {mod.name} ({mod.stat().st_size:,} bytes)")
        else:
            output = Path(self.output_edit.text())
            self.output_path = output
            self.source_size = orig.stat().st_size
            args = ["-d", "-s", str(orig), str(patch), str(output)]
            self.console.appendPlainText(f"Applying xDelta patch...")
            self.console.appendPlainText(f"Original : {orig.name}")
            self.console.appendPlainText(f"Patch    : {patch.name}")

        self.console.appendPlainText("-" * 60)

        self.runner.output_received.connect(self.console.appendPlainText)
        self.runner.finished.connect(self._finished)
        self.runner.run(args)

    def _update_progress(self):
        if self.output_path and self.output_path.exists():
            size = self.output_path.stat().st_size
            percent = int((size / self.source_size) * 100)
            self.progress.setRange(0, 100)
            self.progress.setValue(min(percent, 100))

    def _finished(self, exitCode: int):
        if hasattr(self, "timer"):
            self.timer.stop()

        self.progress.setRange(0, 100)
        self.progress.setValue(100)

        if exitCode != 0:
            QMessageBox.critical(self, "Failed", "xdelta process failed.")
        else:
            # Copy CUE if applying a patch
            if self.mode == "apply" and self.output_path:
                patched_cue = copy_cue_file(Path(self.orig_edit.text()), self.output_path)
                if patched_cue:
                    self.console.appendPlainText(f"CUE file copied to {patched_cue}")

            QMessageBox.information(self, "Success", "Operation completed.")
            if self.output_path:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_path.parent)))

    def _export_log(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Log", "", "*.txt")
        if path:
            Path(path).write_text(self.console.toPlainText())

    def _calculate_checksums(self, path: Path):
        md5 = calculate_hash(path, "md5")
        sha1 = calculate_hash(path, "sha1")
        self.console.appendPlainText(f"MD5: {md5}")
        self.console.appendPlainText(f"SHA1: {sha1}")

    def show_help(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("xPatch Help")
        dialog.setMinimumSize(650, 550)
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(f"""
        <h2>xPatch v{VERSION}</h2>

        <h3><b>What This Tool Does</b></h3>
        Creates and applies xDelta patches for PlayStation 1 BIN files.

        <h3><b>Create Patch</b></h3>
        <ol>
        <li>Select ORIGINAL clean BIN</li>
        <li>Select MODIFIED BIN</li>
        <li>Choose patch save location</li>
        <li>Click Create</li>
        </ol>

        <h3><b>Apply Patch</b></h3>
        <ol>
        <li>Select ORIGINAL clean BIN</li>
        <li>Select .xdelta patch</li>
        <li>Choose output BIN name</li>
        <li>Click Apply</li>
        </ol>

        <h3><b>Checksum Verification</b></h3>
        It is strongly recommended to verify your original BIN checksum
        (MD5 or SHA1) before patching to ensure compatibility.
        Incorrect base files will cause patch failures.

        <h3><b>Resources</b></h3>
        <a href="https://github.com/jmacd/xdelta">xDelta Official GitHub</a>

        <h3><b>License</b></h3>
        This tool uses xdelta3. Please review its respective license.
        xPatch GUI is provided as-is without warranty.
        """)
        layout.addWidget(browser)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        dialog.exec()

    def show_about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("About xPatch")
        dialog.setMinimumSize(50, 30)
        layout = QVBoxLayout(dialog)
        label = QLabel(f"<h2>xPatch</h2>Version {VERSION}<br>Developed by JeevesGB")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(label)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        dialog.exec()