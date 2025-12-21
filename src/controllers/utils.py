from __future__ import annotations

from pathlib import Path
from typing import Callable
from urllib.parse import urlparse
import os

import requests


def log(cb: Callable[[str], None] | None, message: str) -> None:
    if cb:
        cb(message)


def sanitize_filename(name: str) -> str:
    invalid = '<>:"/\\|?*'
    cleaned = "".join("_" if ch in invalid else ch for ch in name)
    cleaned = " ".join(cleaned.split())
    return cleaned.strip() or "archivo"


def url_extension(url: str) -> str:
    path = urlparse(url).path
    return os.path.splitext(path)[1]


def url_filename(url: str) -> str:
    path = urlparse(url).path
    return Path(path).name


def _next_available_path(base_path: Path) -> Path:
    if not base_path.exists():
        return base_path

    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent
    for idx in range(1, 1000):
        candidate = parent / f"{stem}_{idx}{suffix}"
        if not candidate.exists():
            return candidate
    return parent / f"{stem}_extra{suffix}"


def download_binary(url: str, out_path: Path, timeout: int = 30) -> tuple[bool, Path]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    target_path = _next_available_path(out_path)

    try:
        with requests.get(url, stream=True, timeout=timeout, verify=False) as response:
            response.raise_for_status()
            with open(target_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        return True, target_path
    except Exception:
        return False, target_path
