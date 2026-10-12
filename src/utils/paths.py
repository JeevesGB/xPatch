import sys
from pathlib import Path
from shutil import which


def resource_path(relative_path: str | Path) -> Path:
    """Resolve a path relative to the app root (PyInstaller bundle or source tree)."""
    try:
        base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    except Exception:
        # utils/ -> newver/
        base_path = Path(__file__).resolve().parent.parent
    return base_path / relative_path


def find_xdelta() -> Path | None:
    """Locate xdelta3: bundled copy first, then system PATH."""
    candidates = [
        resource_path("tool/xdelta3.exe"),
        resource_path("tool/xdelta3"),
        # Source layout: tool/ lives next to newver/
        Path(__file__).resolve().parent.parent.parent / "tool" / "xdelta3.exe",
        Path(__file__).resolve().parent.parent.parent / "tool" / "xdelta3",
    ]
    for path in candidates:
        if path.is_file():
            return path

    system = which("xdelta3") or which("xdelta3.exe")
    return Path(system) if system else None
