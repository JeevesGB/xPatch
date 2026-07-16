import sys
from pathlib import Path

def resource_path(relative_path: str) -> Path:
    """Get absolute path to resource (supports PyInstaller)."""
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return Path.cwd() / relative_path

def find_xdelta() -> Path | None:
    """Try bundled xdelta first, then system PATH."""
    bundled = resource_path("tool/xdelta3.exe")
    if bundled.exists():
        return bundled

    from shutil import which
    system = which("xdelta3")
    return Path(system) if system else None