from pathlib import Path
from datetime import datetime

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
    QFrame,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QDesktopServices, QIcon, QFont

from services.xdelta_runner import XDeltaRunner
from utils.paths import resource_path, find_xdelta
from utils.checksum import calculate_hash
from utils.files import (
    copy_sidecar_files,
    OPEN_FILTER,
    SAVE_BIN_FILTER,
    PATCH_FILTER,
)

VERSION = "0.2.3"
UPDATE_URL = "https://github.com/JeevesGB/xPatch"
THEME = "ui/theme.qss"
ICON_PATH = resource_path("ico.ico")


def _card() -> QFrame:
    f = QFrame()
    f.setObjectName("card")
    return f


class XPatchWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(f"xPatch  v{VERSION}")
        self.setWindowIcon(QIcon(str(ICON_PATH)))
        self._load_stylesheet()
        self.setMinimumSize(720, 620)
        self.resize(780, 680)
        self.setAcceptDrops(True)

        self.mode = "create"
        self.output_path: Path | None = None
        self.source_size = 0
        self.runner: XDeltaRunner | None = None
        self._progress_timer: QTimer | None = None

        self._init_ui()

    # ================================================================== UI
    def _init_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QFrame()
        header.setObjectName("headerBar")
        header.setFixedHeight(44)
        hdr = QHBoxLayout(header)
        hdr.setContentsMargins(16, 0, 12, 0)
        hdr.setSpacing(8)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_col.setContentsMargins(0, 6, 0, 6)
        app_title = QLabel("xPatch")
        app_title.setObjectName("appTitle")
        app_sub = QLabel(f"v{VERSION}")
        app_sub.setObjectName("appSubtitle")
        title_col.addWidget(app_title)
        title_col.addWidget(app_sub)
        hdr.addLayout(title_col)
        hdr.addStretch()

        self.help_btn = QPushButton("Help")
        self.about_btn = QPushButton("About")
        for b in (self.help_btn, self.about_btn):
            b.setObjectName("secondaryButton")
            b.setFixedWidth(56)
        self.help_btn.clicked.connect(self.show_help)
        self.about_btn.clicked.connect(self.show_about)
        hdr.addWidget(self.help_btn)
        hdr.addWidget(self.about_btn)
        root.addWidget(header)

        # Body
        body = QVBoxLayout()
        body.setContentsMargins(16, 12, 16, 12)
        body.setSpacing(10)
        root.addLayout(body, stretch=1)

        # Mode switcher
        mode_row = QHBoxLayout()
        mode_row.setSpacing(6)

        self.create_btn = QPushButton("Create Patch")
        self.apply_btn = QPushButton("Apply Patch")
        self.create_btn.setObjectName("createPatchButton")
        self.apply_btn.setObjectName("applyPatchButton")
        self.create_btn.setCheckable(True)
        self.apply_btn.setCheckable(True)
        self.create_btn.clicked.connect(lambda: self._set_mode("create"))
        self.apply_btn.clicked.connect(lambda: self._set_mode("apply"))

        mode_row.addWidget(self.create_btn)
        mode_row.addWidget(self.apply_btn)
        mode_row.addStretch()
        body.addLayout(mode_row)

        # Files card
        files_card = _card()
        files_lay = QVBoxLayout(files_card)
        files_lay.setContentsMargins(12, 10, 12, 10)
        files_lay.setSpacing(8)

        files_hdr = QLabel("FILES")
        files_hdr.setObjectName("sectionHeader")
        files_lay.addWidget(files_hdr)

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)
        grid.setColumnStretch(1, 1)

        self.orig_edit = QLineEdit()
        self.mod_edit = QLineEdit()
        self.patch_edit = QLineEdit()
        self.output_edit = QLineEdit()

        self.orig_edit.setPlaceholderText("Original (clean) file…")
        self.mod_edit.setPlaceholderText("Modified file…")
        self.patch_edit.setPlaceholderText(".xdelta / .xd3 patch…")
        self.output_edit.setPlaceholderText("Output path…")

        self.lbl_orig = QLabel("Original")
        self.lbl_mod = QLabel("Modified")
        self.lbl_patch = QLabel("Patch")
        self.lbl_output = QLabel("Output")
        for lbl in (self.lbl_orig, self.lbl_mod, self.lbl_patch, self.lbl_output):
            lbl.setObjectName("fieldLabel")
            lbl.setFixedWidth(60)

        fields = [
            (self.lbl_orig, self.orig_edit),
            (self.lbl_mod, self.mod_edit),
            (self.lbl_patch, self.patch_edit),
            (self.lbl_output, self.output_edit),
        ]

        for row, (label, edit) in enumerate(fields):
            btn = QPushButton("Browse")
            btn.setObjectName("browseButton")
            btn.clicked.connect(lambda _, e=edit: self._browse(e))
            grid.addWidget(label, row, 0, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            grid.addWidget(edit, row, 1)
            grid.addWidget(btn, row, 2)

        files_lay.addLayout(grid)
        body.addWidget(files_card)

        # Action row
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.action_btn = QPushButton("Create xDelta Patch")
        self.action_btn.setObjectName("actionButton")
        self.action_btn.clicked.connect(self._run)

        self.checksum_btn = QPushButton("Checksums")
        self.checksum_btn.setObjectName("secondaryButton")
        self.checksum_btn.setToolTip("Calculate MD5 and SHA1 of the original file")
        self.checksum_btn.setFixedWidth(84)
        self.checksum_btn.clicked.connect(self._on_checksum)

        action_row.addWidget(self.action_btn, stretch=1)
        action_row.addWidget(self.checksum_btn)
        body.addLayout(action_row)

        # Progress card
        prog_card = _card()
        prog_lay = QVBoxLayout(prog_card)
        prog_lay.setContentsMargins(12, 8, 12, 8)
        prog_lay.setSpacing(6)

        prog_top = QHBoxLayout()
        prog_hdr = QLabel("PROGRESS")
        prog_hdr.setObjectName("sectionHeader")
        prog_top.addWidget(prog_hdr)
        prog_top.addStretch()

        status_wrap = QHBoxLayout()
        status_wrap.setSpacing(3)
        self.status_dot = QLabel("●")
        self.status_dot.setObjectName("statusDot")
        self.status_label = QLabel("Ready")
        self.status_label.setObjectName("statusLabel")
        status_wrap.addWidget(self.status_dot)
        status_wrap.addWidget(self.status_label)
        prog_top.addLayout(status_wrap)
        prog_lay.addLayout(prog_top)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%p%")
        self.progress.setFixedHeight(20)
        prog_lay.addWidget(self.progress)
        body.addWidget(prog_card)

        # Log card
        log_card = _card()
        log_lay = QVBoxLayout(log_card)
        log_lay.setContentsMargins(12, 8, 12, 8)
        log_lay.setSpacing(6)

        log_top = QHBoxLayout()
        log_hdr = QLabel("LOG")
        log_hdr.setObjectName("sectionHeader")
        log_top.addWidget(log_hdr)
        log_top.addStretch()

        self.clear_log_btn = QPushButton("Clear")
        self.export_btn = QPushButton("Export")
        for b in (self.clear_log_btn, self.export_btn):
            b.setObjectName("secondaryButton")
            b.setFixedWidth(56)
        self.clear_log_btn.clicked.connect(self._clear_log)
        self.export_btn.clicked.connect(self._export_log)
        log_top.addWidget(self.clear_log_btn)
        log_top.addWidget(self.export_btn)
        log_lay.addLayout(log_top)

        self.console = QPlainTextEdit()
        self.console.setObjectName("console")
        self.console.setReadOnly(True)
        self.console.setMinimumHeight(160)
        self.console.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        mono = QFont("Cascadia Code")
        if not mono.exactMatch():
            mono = QFont("Consolas")
        mono.setStyleHint(QFont.StyleHint.Monospace)
        mono.setPointSize(10)
        self.console.setFont(mono)
        log_lay.addWidget(self.console, stretch=1)
        body.addWidget(log_card, stretch=1)

        self._set_mode("create")
        self._log("Ready.")

    # ============================================================ Helpers
    def _load_stylesheet(self) -> None:
        theme_path = resource_path(THEME)
        if theme_path.exists():
            try:
                self.setStyleSheet(theme_path.read_text(encoding="utf-8"))
            except Exception as e:
                print(f"Failed to load stylesheet: {e}")

    def _log(self, message: str, level: str = "info") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "info": "  ",
            "ok": "✓ ",
            "warn": "! ",
            "error": "x ",
            "cmd": "> ",
        }.get(level, "  ")
        self.console.appendPlainText(f"[{ts}] {prefix}{message}")
        sb = self.console.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _clear_log(self) -> None:
        self.console.clear()
        self._log("Log cleared.")

    def _set_status(self, text: str, state: str = "idle") -> None:
        colors = {
            "idle": "#555",
            "busy": "#3b82f6",
            "ok": "#22c55e",
            "error": "#ef4444",
        }
        self.status_dot.setStyleSheet(f"color: {colors.get(state, '#555')};")
        self.status_label.setText(text)

    def _set_progress(self, value: int, indeterminate: bool = False) -> None:
        if indeterminate:
            self.progress.setRange(0, 0)
            self.progress.setFormat("…")
        else:
            self.progress.setRange(0, 100)
            self.progress.setValue(max(0, min(100, value)))
            self.progress.setFormat("%p%")

    def _start_progress_timer(self) -> None:
        self._stop_progress_timer()
        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(250)
        self._progress_timer.timeout.connect(self._poll_progress)
        self._progress_timer.start()

    def _stop_progress_timer(self) -> None:
        if self._progress_timer is not None:
            self._progress_timer.stop()
            self._progress_timer.deleteLater()
            self._progress_timer = None

    def _poll_progress(self) -> None:
        if self.mode != "apply" or not self.output_path or self.source_size <= 0:
            return
        try:
            if self.output_path.exists():
                size = self.output_path.stat().st_size
                percent = min(int((size / self.source_size) * 100), 99)
                self._set_progress(percent)
                mb_done = size / (1024 * 1024)
                mb_total = self.source_size / (1024 * 1024)
                self._set_status(
                    f"{mb_done:.1f} / {mb_total:.1f} MB  ({percent}%)",
                    "busy",
                )
        except OSError:
            pass

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
        self._set_status("Ready" if is_create else "Ready", "idle")

    # ======================================================== Drag & Drop
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if not path.is_file():
                continue

            suffix = path.suffix.lower()
            if suffix in (".xdelta", ".xd3"):
                self.patch_edit.setText(str(path))
                self._log(f"Dropped patch: {path.name}")
                continue

            if not self.orig_edit.text():
                self.orig_edit.setText(str(path))
                self._log(f"Dropped original: {path.name}")
            elif self.mode == "create" and not self.mod_edit.text():
                self.mod_edit.setText(str(path))
                self._log(f"Dropped modified: {path.name}")
            elif self.mode == "apply" and not self.output_edit.text():
                suggested = path.with_name(path.stem + "_patched" + path.suffix)
                self.output_edit.setText(str(suggested))
                self._log(f"Suggested output: {suggested.name}")

    # ============================================================ Browse
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
            self._log(f"Selected: {Path(path).name}")

    # ======================================================== Validation
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
            if not str(patch) or not patch.parent.exists():
                QMessageBox.critical(self, "Error", "Choose a valid patch save location.")
                return False
        else:
            patch = Path(self.patch_edit.text().strip())
            if not patch.is_file():
                QMessageBox.critical(self, "Error", "Patch file is missing or invalid.")
                return False
            output = Path(self.output_edit.text().strip())
            if not str(output) or not output.parent.exists():
                QMessageBox.critical(self, "Error", "Choose a valid output location.")
                return False

        return True

    # ================================================================ Run
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

        self.action_btn.setEnabled(False)
        self._set_progress(0, indeterminate=True)
        self._set_status("Starting…", "busy")

        self.runner = XDeltaRunner(xdelta)
        self.runner.output_received.connect(self._on_runner_output)
        self.runner.finished.connect(self._finished)

        if self.mode == "create":
            mod = Path(self.mod_edit.text().strip())
            args = ["-e", "-s", str(orig), str(mod), str(patch)]
            self._log("Creating patch…", "cmd")
            self._log(f"Original : {orig.name}  ({orig.stat().st_size:,} bytes)")
            self._log(f"Modified : {mod.name}  ({mod.stat().st_size:,} bytes)")
            self._log(f"Patch    : {patch.name}")
            self._set_status("Encoding…", "busy")
        else:
            output = Path(self.output_edit.text().strip())
            self.output_path = output
            self.source_size = orig.stat().st_size
            args = ["-d", "-s", str(orig), str(patch), str(output)]
            self._log("Applying patch…", "cmd")
            self._log(f"Original : {orig.name}")
            self._log(f"Patch    : {patch.name}")
            self._log(f"Output   : {output.name}")
            self._set_status("Decoding…", "busy")
            self._set_progress(0)
            self._start_progress_timer()

        self._log("-" * 40)
        self.runner.run(args)

    def _on_runner_output(self, text: str) -> None:
        lower = text.lower()
        if "error" in lower or "failed" in lower:
            self._log(text, "error")
        elif "success" in lower or "finished successfully" in lower:
            self._log(text, "ok")
        elif text.startswith("Running:"):
            self._log(text, "cmd")
        else:
            self._log(text)

    def _finished(self, exit_code: int) -> None:
        self._stop_progress_timer()
        self.action_btn.setEnabled(True)

        if exit_code != 0:
            self._set_progress(0)
            self._set_status("Failed", "error")
            self._log(f"Failed (exit {exit_code})", "error")
            QMessageBox.critical(
                self, "Failed", "xdelta process failed. Check the log for details."
            )
            return

        self._set_progress(100)
        self._set_status("Done", "ok")

        if self.mode == "apply" and self.output_path:
            copied = copy_sidecar_files(
                Path(self.orig_edit.text().strip()), self.output_path
            )
            for p in copied:
                self._log(f"Sidecar → {p.name}", "ok")

        self._log("Done.", "ok")
        QMessageBox.information(self, "Success", "Operation completed.")
        if self.output_path and self.output_path.parent.exists():
            QDesktopServices.openUrl(
                QUrl.fromLocalFile(str(self.output_path.parent))
            )

    # ========================================================== Checksums
    def _on_checksum(self) -> None:
        path_str = self.orig_edit.text().strip()
        if not path_str:
            QMessageBox.warning(self, "Checksum", "Select an original file first.")
            return
        path = Path(path_str)
        if not path.is_file():
            QMessageBox.critical(self, "Checksum", "Original file not found.")
            return

        self._log(f"Checksums: {path.name}")
        self._set_status("Hashing…", "busy")
        self._set_progress(0, indeterminate=True)
        try:
            md5 = calculate_hash(path, "md5")
            sha1 = calculate_hash(path, "sha1")
            self._log(f"MD5  {md5}", "ok")
            self._log(f"SHA1 {sha1}", "ok")
            self._set_status("Ready", "ok")
        except Exception as e:
            self._log(f"Checksum error: {e}", "error")
            self._set_status("Failed", "error")
        finally:
            self._set_progress(0)

    def _export_log(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Log", "xpatch_log.txt", "Text Files (*.txt)"
        )
        if path:
            Path(path).write_text(self.console.toPlainText(), encoding="utf-8")
            self._log(f"Exported: {Path(path).name}", "ok")

    # ============================================================ Dialogs
    def show_help(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Help")
        dialog.setMinimumSize(560, 480)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(8)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(
            f"""
        <h3 style="color:#eee; margin:0 0 8px 0;">xPatch v{VERSION}</h3>
        <p style="color:#888; margin:0 0 12px 0;">Create and apply xDelta patches for disk images and ROMs.</p>

        <p style="color:#666; font-size:11px; margin:0 0 4px 0;"><b style="color:#aaa;">FORMATS</b></p>
        <p style="color:#888; margin:0 0 12px 0; font-size:12px;">
          .bin .cue .iso .img .mdf .nrg .ccd .rom .gcm .chd .cso .wbfs .rvz
        </p>

        <p style="color:#666; font-size:11px; margin:0 0 4px 0;"><b style="color:#aaa;">CREATE</b></p>
        <ol style="color:#888; font-size:12px; margin:0 0 12px 0; padding-left:18px;">
          <li>Original (clean) file</li>
          <li>Modified file</li>
          <li>Save location for .xdelta</li>
          <li>Click Create</li>
        </ol>

        <p style="color:#666; font-size:11px; margin:0 0 4px 0;"><b style="color:#aaa;">APPLY</b></p>
        <ol style="color:#888; font-size:12px; margin:0 0 12px 0; padding-left:18px;">
          <li>Original (clean) file</li>
          <li>.xdelta / .xd3 patch</li>
          <li>Output path</li>
          <li>Click Apply</li>
        </ol>
        <p style="color:#666; font-size:12px;">Sidecars (.cue, .ccd, .sub…) are copied automatically.</p>

        <p style="margin-top:12px;">
          <a href="https://github.com/jmacd/xdelta" style="color:#3b82f6;">xDelta</a>
          &nbsp;·&nbsp;
          <a href="{UPDATE_URL}" style="color:#3b82f6;">xPatch</a>
        </p>
        """
        )
        layout.addWidget(browser)
        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondaryButton")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        dialog.exec()

    def show_about(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("About")
        dialog.setFixedSize(280, 150)
        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(16, 16, 16, 12)
        layout.setSpacing(4)

        title = QLabel("xPatch")
        title.setObjectName("appTitle")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ver = QLabel(f"v{VERSION}  ·  JeevesGB")
        ver.setObjectName("appSubtitle")
        ver.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title)
        layout.addWidget(ver)
        layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondaryButton")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)
        dialog.exec()
