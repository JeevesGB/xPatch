import sys
from PyQt6.QtWidgets import QApplication
from ui.main_window import XPatchWindow

def main() -> None:
    app = QApplication(sys.argv)
    window = XPatchWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()