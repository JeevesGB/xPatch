from pathlib import Path
import shutil

# Common disk-image / ROM extensions supported by the UI
SUPPORTED_EXTENSIONS = (
    ".bin",
    ".iso",
    ".img",
    ".rom",
    ".cue",
    ".ccd",
    ".mds",
    ".nrg",
    ".mdf",
    ".chd",
    ".gcm",
    ".cso",
    ".wbfs",
    ".wia",
    ".rvz",
)

# Human-readable filter string for QFileDialog
OPEN_FILTER = (
    "Disk Images / ROMs ("
    + " ".join(f"*{ext}" for ext in SUPPORTED_EXTENSIONS)
    + ");;All Files (*)"
)

SAVE_BIN_FILTER = (
    "Disk Images ("
    + " ".join(f"*{ext}" for ext in (".bin", ".iso", ".img", ".rom"))
    + ");;All Files (*)"
)

PATCH_FILTER = "xDelta Patches (*.xdelta *.xd3);;All Files (*)"


def copy_sidecar_files(original: Path, patched: Path) -> list[Path]:
    """
    Copy common sidecar files that accompany disk images so the patched
    image remains usable (e.g. .cue for .bin, .ccd/.sub for CloneCD, etc.).

    Returns a list of paths that were successfully copied.
    """
    copied: list[Path] = []
    # Extensions that often live next to the main image and should be
    # renamed to match the patched output.
    sidecar_suffixes = (".cue", ".ccd", ".sub", ".img", ".toc", ".mds", ".mdf")

    for suffix in sidecar_suffixes:
        src = original.with_suffix(suffix)
        if not src.exists() or src == original:
            continue
        dst = patched.with_suffix(suffix)
        try:
            shutil.copy2(src, dst)
            copied.append(dst)
        except OSError:
            pass

    return copied


def is_supported_file(path: Path) -> bool:
    return path.suffix.lower() in SUPPORTED_EXTENSIONS or path.suffix.lower() in (
        ".xdelta",
        ".xd3",
    )
