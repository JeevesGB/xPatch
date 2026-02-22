import sys
import os
import re
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QFileDialog, QMessageBox, QGridLayout, QHBoxLayout,
    QPlainTextEdit, QVBoxLayout, QProgressBar,
    QDialog, QTextBrowser
)
from PyQt6.QtCore import Qt, QProcess, QTimer, QPropertyAnimation
from PyQt6.QtGui import QDesktopServices, QIcon
from PyQt6.QtCore import QUrl

VERSION = "0.0.1"
UPDATE_URL = "https://yourwebsite.com/xpatch"   # change this

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and PyInstaller """
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class XPatchWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"xPatch v{VERSION}")
        self.setWindowIcon(QIcon(resource_path("ico.ico")))
        self.setMinimumSize(750, 600)

        self.mode = "create"
        self.process = None
        self.output_path = None
        self.source_size = 0

        self.init_ui()
        self.load_stylesheet()
        self.update_mode()

    # ---------------- UI ---------------- #

    def init_ui(self):
        main_layout = QVBoxLayout()
        self.form_layout = QGridLayout()

        self.create_btn = QPushButton("Create Patch")
        self.apply_btn = QPushButton("Apply Patch")
        self.help_btn = QPushButton("?")
        self.about_btn = QPushButton("About")
        self.help_btn.setFixedWidth(35)

        self.create_btn.clicked.connect(lambda: self.set_mode("create"))
        self.apply_btn.clicked.connect(lambda: self.set_mode("apply"))
        self.help_btn.clicked.connect(self.show_help)
        self.about_btn.clicked.connect(self.show_about)

        mode_layout = QHBoxLayout()
        mode_layout.addWidget(self.create_btn)
        mode_layout.addWidget(self.apply_btn)
        mode_layout.addStretch()
        mode_layout.addWidget(self.help_btn)
        mode_layout.addWidget(self.about_btn)

        self.orig_edit = QLineEdit()
        self.mod_edit = QLineEdit()
        self.patch_edit = QLineEdit()
        self.output_edit = QLineEdit()

        self.orig_btn = QPushButton("Browse")
        self.mod_btn = QPushButton("Browse")
        self.patch_btn = QPushButton("Browse")
        self.output_btn = QPushButton("Browse")

        self.orig_btn.clicked.connect(self.browse_original)
        self.mod_btn.clicked.connect(self.browse_modified)
        self.patch_btn.clicked.connect(self.browse_patch)
        self.output_btn.clicked.connect(self.browse_output)

        self.action_btn = QPushButton()
        self.action_btn.setFixedHeight(40)
        self.action_btn.clicked.connect(self.run_action)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)

        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)

        # Layout
        self.form_layout.addLayout(mode_layout, 0, 0, 1, 3)

        self.form_layout.addWidget(QLabel("Original BIN:"), 1, 0)
        self.form_layout.addWidget(self.orig_edit, 1, 1)
        self.form_layout.addWidget(self.orig_btn, 1, 2)

        self.form_layout.addWidget(QLabel("Modified BIN:"), 2, 0)
        self.form_layout.addWidget(self.mod_edit, 2, 1)
        self.form_layout.addWidget(self.mod_btn, 2, 2)

        self.form_layout.addWidget(QLabel("xDelta Patch:"), 3, 0)
        self.form_layout.addWidget(self.patch_edit, 3, 1)
        self.form_layout.addWidget(self.patch_btn, 3, 2)

        self.form_layout.addWidget(QLabel("Output BIN:"), 4, 0)
        self.form_layout.addWidget(self.output_edit, 4, 1)
        self.form_layout.addWidget(self.output_btn, 4, 2)

        self.form_layout.addWidget(self.action_btn, 5, 0, 1, 3)

        main_layout.addLayout(self.form_layout)
        main_layout.addWidget(self.progress)
        main_layout.addWidget(QLabel("Console Output:"))
        main_layout.addWidget(self.console)

        self.setLayout(main_layout)

    def load_stylesheet(self):
        theme_path = resource_path("theme.qss")
        if os.path.exists(theme_path):
            with open(theme_path, "r") as f:
                self.setStyleSheet(f.read())

    # ---------------- FILE BROWSERS ---------------- #

    def browse_original(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Original BIN", "", "BIN files (*.bin)"
        )
        if path:
            self.orig_edit.setText(path)

    def browse_modified(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select Modified BIN", "", "BIN files (*.bin)"
        )
        if path:
            self.mod_edit.setText(path)

    def browse_patch(self):
        if self.mode == "create":
            path, _ = QFileDialog.getSaveFileName(
                self, "Save xDelta Patch", "", "xDelta Patch (*.xdelta)"
            )
            if path and not path.lower().endswith(".xdelta"):
                path += ".xdelta"
        else:
            path, _ = QFileDialog.getOpenFileName(
                self, "Select xDelta Patch", "", "xDelta Patch (*.xdelta)"
            )

        if path:
            self.patch_edit.setText(path)

    def browse_output(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Output BIN", "", "BIN files (*.bin)"
        )
        if path and not path.lower().endswith(".bin"):
            path += ".bin"

        if path:
            self.output_edit.setText(path)


    # ---------------- Mode ---------------- #

    def set_mode(self, mode):
        self.mode = mode
        self.update_mode()

    def update_mode(self):
        is_create = self.mode == "create"

        self.mod_edit.setVisible(is_create)
        self.mod_btn.setVisible(is_create)
        self.form_layout.itemAtPosition(2, 0).widget().setVisible(is_create)

        self.output_edit.setVisible(not is_create)
        self.output_btn.setVisible(not is_create)
        self.form_layout.itemAtPosition(4, 0).widget().setVisible(not is_create)

        self.action_btn.setText("Create xDelta Patch" if is_create else "Apply Patch")

    # ---------------- Process ---------------- #

    def run_action(self):
        orig = self.orig_edit.text()
        patch = self.patch_edit.text()

        if not orig or not patch:
            QMessageBox.critical(self, "Error", "Missing required files.")
            return

        # Use resource_path for xdelta3.exe location
        xdelta_exe = resource_path(os.path.join("tool", "xdelta3.exe"))
        if not os.path.exists(xdelta_exe):
            QMessageBox.critical(self, "Error", "xdelta3.exe not found.")
            return

        self.console.clear()
        self.progress.setValue(0)
        self.action_btn.setEnabled(False)

        self.process = QProcess(self)
        self.process.setProgram(xdelta_exe)

        if self.mode == "create":
            mod = self.mod_edit.text()
            if not mod:
                QMessageBox.critical(self, "Error", "Select the modified BIN.")
                return
            args = ["-v", "-e", "-s", orig, mod, patch]
        else:
            output_bin = self.output_edit.text()
            if not output_bin:
                QMessageBox.critical(self, "Error", "Choose output BIN.")
                return

            args = ["-v", "-d", "-s", orig, patch, output_bin]
            self.output_path = output_bin
            self.source_size = os.path.getsize(orig)

            self.timer = QTimer()
            self.timer.timeout.connect(self.update_progress)
            self.timer.start(300)

        self.process.setArguments(args)
        self.process.readyReadStandardOutput.connect(self.handle_stdout)
        self.process.readyReadStandardError.connect(self.handle_stderr)
        self.process.finished.connect(self.process_finished)
        self.process.start()

    def update_progress(self):
        if self.output_path and os.path.exists(self.output_path):
            current_size = os.path.getsize(self.output_path)
            percent = int((current_size / self.source_size) * 100)
            self.progress.setValue(min(percent, 100))

    def handle_stdout(self):
        output = self.process.readAllStandardOutput().data().decode()
        self.console.appendPlainText(output)

        # Parse verbose processed bytes
        match = re.search(r"processed\s+(\d+)\s+bytes", output)

        if match and self.source_size > 0:
            processed_bytes = int(match.group(1))
            percent = int((processed_bytes / self.source_size) * 100)
            self.progress.setValue(min(percent, 100))

    def handle_stderr(self):
        self.console.appendPlainText(self.process.readAllStandardError().data().decode())

    def process_finished(self):
        if hasattr(self, "timer"):
            self.timer.stop()
        self.progress.setValue(100)
        self.action_btn.setEnabled(True)
        self.console.appendPlainText("\nProcess finished.")

    # ---------------- HELP ---------------- #

    def show_help(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("xPatch Help")
        dialog.setMinimumSize(650, 550)

        layout = QVBoxLayout()

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

        update_btn = QPushButton("Check for Updates")
        update_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(UPDATE_URL)))
        layout.addWidget(update_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)
        dialog.exec()

    # ---------------- ABOUT (Animated) ---------------- #

    def show_about(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("About xPatch")
        dialog.setMinimumSize(500, 300)

        layout = QVBoxLayout()

        label = QLabel(f"""
        <h2>xPatch</h2>
        Version: {VERSION}<br><br>
        A modern GUI wrapper for xdelta3.<br><br>
        Developed by JeevesGB.
        """)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setTextFormat(Qt.TextFormat.RichText)

        layout.addWidget(label)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dialog.close)
        layout.addWidget(close_btn)

        dialog.setLayout(layout)

        # Fade-in animation
        dialog.setWindowOpacity(0)
        animation = QPropertyAnimation(dialog, b"windowOpacity")
        animation.setDuration(400)
        animation.setStartValue(0)
        animation.setEndValue(1)
        animation.start()

        dialog.exec()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = XPatchWindow()
    window.show()
    sys.exit(app.exec())