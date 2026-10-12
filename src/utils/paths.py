import sys
from pathlib import Path

import sys
from pathlib import Path

def resource_path(relative_path):
    """Get path to resource"""
    try:
        base_path = Path(sys._MEIPASS)
    except Exception:
        base_path = Path(__file__).parent.parent  # Go up to 'newver' folder
    
    return base_path / relative_path

def find_xdelta() -> Path | None:
    """Try bundled xdelta first, then system PATH."""
    bundled = resource_path("tool/xdelta3.exe")
    if bundled.exists():
        return bundled

    from shutil import which
    system = which("xdelta3")
    return Path(system) if system else None