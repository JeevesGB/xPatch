from pathlib import Path
import shutil

def copy_cue_file(original_bin: Path, patched_bin: Path) -> Path | None:
    """
    Copy the .cue file corresponding to the original BIN and rename it
    to match the patched BIN. Returns the new cue path, or None if no cue exists.
    """
    orig_cue = original_bin.with_suffix(".cue")
    if orig_cue.exists():
        patched_cue = patched_bin.with_suffix(".cue")
        shutil.copy(orig_cue, patched_cue)
        return patched_cue
    return None