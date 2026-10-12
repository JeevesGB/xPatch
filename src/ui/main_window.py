from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QPushButton,
    QLabel,
    QLineEdit,
    QProgressBar,
    QPlainTextEdit,
    QFileDialog,
    QMessageBox,
    QDialog,
    QTextBrowser,
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices, QIcon

from services.xdelta_runner import XDeltaRunner
from utils.paths import resource_path, find_xdelta
from utils.checksum import calculate_hash
from utils.files import (
    copy_sidecar_files,
    OPEN_FILTER,
    SAVE_BIN_FILTER,
    PATCH_FILTER,
    is_supported_file,
)

VERSION = "0.2.0"
UPDATE_URL = "https://github.com/JeevesGB/xPatch"
THEME = "ui/theme.qss"
ICON_PATH = resource_path("ico.ico")


class XPatchWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"xPatch v{VERSION}")
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self._load_stylesheet()
        self.setMinimumSize(780, 640)
        self.setAcceptDrops(True)

        self.mode = "create"
        self.output_path: Path | None = None
        self.source_size = 0
        self.runner: XDeltaRunner | None = None

        self._init_ui()

    # ------------------------------------------------------------------ UI
    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        grid = QGridLayout()

        # Mode buttons
        self.create_btn = QPushButton("Create Patch")
        self.apply_btn = QPushButton("Apply Patch")
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

        # Generic labels – works for .bin, .iso, .img, ROMs, etc.
        self.lbl_orig = QLabel("Original File:")
        self.lbl_mod = QLabel("Modified File:")
        self.lbl_patch = QLabel("xDelta Patch:")
        self.lbl_output = QLabel("Output File:")

        fields = [
            (self.lbl_orig, self.orig_edit),
            (self.lbl_mod, self.mod_edit),
            (self.lbl_patch, self.patch_edit),
            (self.lbl_output, self.output_edit),
        ]

        for row, (label, edit) in enumerate(fields, start=1):
            btn = QPushButton("Browse")
            btn.clicked.connect(lambda _, e=edit: self._browse(e))
            grid.addWidget(label, row, 0)
            grid.addWidget(edit, row, 1)
            grid.addWidget(btn, row, 2)

        self.action_btn = QPushButton("Create xDelta Patch")
        self.action_btn.clicked.connect(self._run)
        grid.addWidget(self.action_btn, 5, 0, 1, 3)

        # Optional checksum button
        checksum_row = QHBoxLayout()
        self.checksum_btn = QPushButton("Calculate Checksums (Original)")
        self.checksum_btn.clicked.connect(self._on_checksum)
        checksum_row.addWidget(self.checksum_btn)
        checksum_row.addStretch()
        grid.addLayout(checksum_row, 6, 0, 1, 3)

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
        theme_path = resource_path(THEME)
        if theme_path.exists():
            try:
                self.setStyleSheet(theme_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"Failed to load stylesheet: {e}")

    def _set_mode(self, mode: str) -> None:
        self.mode = mode
        is_create = mode == "create"

        self.create_btn.setChecked(is_create)
        self.apply_btn.setChecked(not is_create)

        self.mod_edit.setEnabled(is_create)
        self.lbl_mod.setEnabled(is_create)
        self.output_edit.setEnabled(not is_create)
        self.lbl_output.setEnabled(not is_create)

        self.action_btn.setText(
            "Create xDelta Patch" if is_create else "Apply Patch"
        )

    # -------------------------------------------------------------- Drag & Drop
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if not path.is_file():
                continue

            suffix = path.suffix.lower()
            # Prefer putting patch files into the patch field
            if suffix in (".xdelta", ".xd3"):
                self.patch_edit.setText(str(path))
                continue

            if not self.orig_edit.text():
                self.orig_edit.setText(str(path))
            elif self.mode == "create" and not self.mod_edit.text():
                self.mod_edit.setText(str(path))
            elif not self.patch_edit.text() and suffix in (".xdelta", ".xd3"):
                self.patch_edit.setText(str(path))
            elif self.mode == "apply" and not self.output_edit.text():
                # Suggest an output name next to the original
                suggested = path.with_name(path.stem + "_patched" + path.suffix)
                self.output_edit.setText(str(suggested))

    # ---------------------------------------------------------------- Browse
    def _browse(self, edit: QLineEdit) -> None:
        if edit is self.patch_edit:
            if self.mode == "create":
                path, _ = QFileDialog.getSaveFileName(
                    self, "Save Patch", "", PATCH_FILTER
                )
            else:
                path, _ = QFileDialog.getOpenFileName(
                    self, "Open Patch", "", PATCH_FILTER
                )
        elif edit is self.output_edit:
            path, _ = QFileDialog.getSaveFileName(
                self, "Save Output", "", SAVE_BIN_FILTER
            )
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "Open File", "", OPEN_FILTER
            )

        if path:
            edit.setText(path)

    # ------------------------------------------------------------- Validation
    def _validate(self) -> bool:
        orig = Path(self.orig_edit.text().strip())
        if not orig.is_file():
            QMessageBox.critical(self, "Error", "Original file is missing or invalid.")
            return False

        if self.mode == "create":
            mod = Path(self.mod_edit.text().strip())
            if not mod.is_file():
                QMessageBox.critical(self, "Error", "Modified file is missing or invalid.")
                return False
            if orig.resolve() == mod.resolve():
                QMessageBox.warning(
                    self, "Error", "Original and Modified files cannot be the same."
                )
                return False
            patch = Path(self.patch_edit.text().strip())
            if not patch.parent.exists():
                QMessageBox.critical(self, "Error", "Patch output folder does not exist.")
                return False
        else:
            patch = Path(self.patch_edit.text().strip())
            if not patch.is_file():
                QMessageBox.critical(self, "Error", "Patch file is missing or invalid.")
                return False
            output = Path(self.output_edit.text().strip())
            if not output.parent.exists():
                QMessageBox.critical(self, "Error", "Output folder does not exist.")
                return False

        return True

    # ----------------------------------------------------------------- Run
    def _run(self) -> None:
        if not self._validate():
            return

        xdelta = find_xdelta()
        if not xdelta:
            QMessageBox.critical(
                self,
                "Error",
                "xdelta3 not found.\nPlace xdelta3.exe in the tool/ folder or install it on PATH.",
            )
            return

        if self.runner and self.runner.is_running():
            QMessageBox.information(self, "Busy", "A process is already running.")
            return

        orig = Path(self.orig_edit.text().strip())
        patch = Path(self.patch_edit.text().strip())

        self.console.clear()
        self.progress.setRange(0, 0)  # indeterminate

        self.runner = XDeltaRunner(xdelta)
        self.runner.output_received.connect(self.console.appendPlainText)
        self.runner.finished.connect(self._finished)

        if self.mode == "create":
            mod = Path(self.mod_edit.text().strip())
            # -e = encode, -s = source (original)
            args = ["-e", "-s", str(orig), str(mod), str(patch)]
            self.console.appendPlainText("Creating xDelta patch…")
            self.console.appendPlainText(
                f"Original : {orig.name} ({orig.stat().st_size:,} bytes)"
            )
            self.console.appendPlainText(
                f"Modified : {mod.name} ({mod.stat().st_size:,} bytes)"
            )
            self.console.appendPlainText(f"Patch    : {patch.name}")
        else:
            output = Path(self.output_edit.text().strip())
            self.output_path = output
            self.source_size = orig.stat().st_size
            # -d = decode, -s = source (original)
            args = ["-d", "-s", str(orig), str(patch), str(output)]
            self.console.appendPlainText("Applying xDelta patch…")
            self.console.appendPlainText(f"Original : {orig.name}")
            self.console.appendPlainText(f"Patch    : {patch.name}")
            self.console.appendPlainText(f"Output   : {output.name}")

        self.console.appendPlainText("-" * 60)
        self.runner.run(args)

    def _finished(self, exit_code: int) -> None:
        self.progress.setRange(0, 100)
        self.progress.setValue(100)

        if exit_code != 0:
            QMessageBox.critical(self, "Failed", "xdelta process failed. Check the console log.")
            return

        # Copy common sidecar files (cue, ccd, etc.) when applying
        if self.mode == "apply" and self.output_path:
            copied = copy_sidecar_files(
                Path(self.orig_edit.text().strip()), self.output_path
            )
            for p in copied:
                self.console.appendPlainText(f"Sidecar copied → {p.name}")

        QMessageBox.information(self, "Success", "Operation completed successfully.")
        if self.output_path and self.output_path.parent.exists():
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self.output_path.parent))
            )

    # ------------------------------------------------------------- Helpers
    def _on_checksum(self) -> None:
        path_str = self.orig_edit.text().strip()
        if not path_str:
            QMessageBox.warning(self, "Checksum", "Select an original file first.")
            return
        path = Path(path_str)
        if not path.is_file():
            QMessageBox.critical(self, "Checksum", "Original file not found.")
            return

        self.console.appendPlainText(f"Calculating checksums for {path.name}…")
        try:
            md5 = calculate_hash(path, "md5")
            sha1 = calculate_hash(path, "sha1")
            self.console.appendPlainText(f"MD5 : {md5}")
            self.console.appendPlainText(f"SHA1: {sha1}")
        except Exception as e:
            self.console.appendPlainText(f"Checksum error: {e}")

    def _export_log(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Save Log", "", "Text Files (*.txt)")
        if path:
            Path(path).write_text(self.console.toPlainText(), encoding="utf-8")

    # --------------------------------------------------------------- Dialogs
    def show_help(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("xPatch Help")
        dialog.setMinimumSize(680, 580)
        layout = QVBoxLayout(dialog)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(
            f"""
        <h2>xPatch v{VERSION}</h2>

        <h3>What This Tool Does</h3>
        <p>
        Creates and applies <b>xDelta</b> binary patches for disk images and ROMs.
        Supported file types include:
        </p>
        <ul>
          <li><code>.bin</code> / <code>.cue</code> (PlayStation, etc.)</li>
          <li><code>.iso</code> (CD/DVD images)</li>
          <li><code>.img</code>, <code>.mdf</code>, <code>.nrg</code>, <code>.ccd</code></li>
          <li><code>.rom</code>, <code>.gcm</code>, <code>.chd</code>, <code>.cso</code>, <code>.wbfs</code>, <code>.rvz</code> …</li>
        </ul>

        <h3>Create Patch</h3>
        <ol>
          <li>Select the <b>Original</b> (clean) file</li>
          <li>Select the <b>Modified</b> file</li>
          <li>Choose where to save the <code>.xdelta</code> patch</li>
          <li>Click <b>Create xDelta Patch</b></li>
        </ol>

        <h3>Apply Patch</h3>
        <ol>
          <li>Select the <b>Original</b> (clean) file</li>
          <li>Select the <code>.xdelta</code> / <code>.xd3</code> patch</li>
          <li>Choose the output filename (e.g. <code>game_patched.iso</code>)</li>
          <li>Click <b>Apply Patch</b></li>
        </ol>
        <p>
        When applying, common sidecar files (<code>.cue</code>, <code>.ccd</code>,
        <code>.sub</code>, …) that sit next to the original are automatically
        copied and renamed to match the output.
        </p>

        <h3>Checksum Verification</h3>
        <p>
        Use the <b>Calculate Checksums</b> button to verify your original file
        (MD5 / SHA1) before patching. Incorrect base files will cause the patch
        to fail or produce a broken result.
        </p>

        <h3>Drag &amp; Drop</h3>
        <p>
        You can drop files directly onto the window. Patch files
        (<code>.xdelta</code> / <code>.xd3</code>) go into the patch field;
        other supported images fill the next empty slot.
        </p>

        <h3>Resources</h3>
        <p>
          <a href="https://github.com/jmacd/xdelta">xDelta official repository</a><br>
          <a href="{UPDATE_URL}">xPatch on GitHub</a>
        </p>

        <h3>License</h3>
        <p>
        This tool uses xdelta3 – please review its license.
        xPatch GUI is provided as-is without warranty (MIT).
        </p>
        """
        )
        layout.addWidget(browser)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        dialog.exec()

    def show_about(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("About xPatch")
        dialog.setMinimumSize(280, 140)
        layout = QVBoxLayout(dialog)
        label = QLabel(
            f"<h2>xPatch</h2>"
            f"Version {VERSION}<br>"
            f"Developed by JeevesGB<br><br>"
            f"Supports .bin · .iso · .img · .rom and more"
        )
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(label)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        dialog.exec()
