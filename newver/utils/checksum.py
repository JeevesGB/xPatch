import hashlib
from pathlib import Path

def calculate_hash(path: Path, algorithm: str = "md5") -> str:
    hash_func = hashlib.new(algorithm)
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hash_func.update(chunk)
    return hash_func.hexdigest()