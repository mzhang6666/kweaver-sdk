"""Normalize .bkn file bytes to UTF-8 for BKN import (validate / push)."""

from __future__ import annotations

import shutil
import tempfile
from collections.abc import Callable
from pathlib import Path

from charset_normalizer import from_bytes

# Minimum chaos score from charset-normalizer (0 = clean; higher = messier).
# Reject detection when the best match is too messy.
_BKN_MAX_CHAOS = 0.35


def normalize_bkn_file_bytes(
    raw: bytes,
    *,
    detect_encoding: bool,
    source_encoding: str | None,
    file_label: str,
) -> bytes:
    """Decode .bkn bytes and return UTF-8 encoded bytes (no BOM)."""
    if source_encoding:
        enc = source_encoding.strip().lower()
        if enc in ("utf-8", "utf8"):
            body = raw[3:] if raw.startswith(b"\xef\xbb\xbf") else raw
            body.decode("utf-8")  # strict
            return body
        return raw.decode(source_encoding).encode("utf-8")

    if not detect_encoding:
        body = raw[3:] if raw.startswith(b"\xef\xbb\xbf") else raw
        body.decode("utf-8")
        return body

    work = raw[3:] if raw.startswith(b"\xef\xbb\xbf") else raw
    try:
        work.decode("utf-8")
        return work
    except UnicodeDecodeError:
        pass

    result = from_bytes(work)
    best = result.best()
    if best is None:
        raise ValueError(
            f"Could not detect encoding for {file_label}. "
            "Try --source-encoding gb18030 or save files as UTF-8."
        )
    if best.chaos > _BKN_MAX_CHAOS:
        raise ValueError(
            f"Encoding detection uncertain for {file_label} (chaos={best.chaos:.3f}). "
            "Try --source-encoding gb18030 or save files as UTF-8."
        )
    text = str(best)
    return text.encode("utf-8")


def copy_bkn_tree_with_utf8_bkn(
    src_root: Path,
    dest_root: Path,
    *,
    detect_encoding: bool,
    source_encoding: str | None,
) -> None:
    """Copy directory tree; rewrite each ``.bkn`` file as UTF-8."""
    src_root = src_root.resolve()
    dest_root = dest_root.resolve()
    for path in src_root.rglob("*"):
        if not path.is_file():
            continue
        rel = path.relative_to(src_root)
        out = dest_root / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        if path.suffix.lower() == ".bkn":
            raw = path.read_bytes()
            label = str(rel).replace("\\", "/")
            normalized = normalize_bkn_file_bytes(
                raw,
                detect_encoding=detect_encoding,
                source_encoding=source_encoding,
                file_label=label,
            )
            out.write_bytes(normalized)
        else:
            shutil.copy2(path, out)


def prepare_bkn_directory_for_import(
    abs_dir: Path,
    *,
    detect_encoding: bool,
    source_encoding: str | None,
) -> tuple[Path, Callable[[], None]]:
    """Return directory path for ``load_network`` and a cleanup callable."""
    need_work = source_encoding is not None or detect_encoding
    abs_dir = abs_dir.resolve()
    if not need_work:
        return abs_dir, lambda: None

    tmp = Path(tempfile.mkdtemp(prefix="kweaver-bkn-"))
    copy_bkn_tree_with_utf8_bkn(
        abs_dir,
        tmp,
        detect_encoding=detect_encoding,
        source_encoding=source_encoding,
    )

    def cleanup() -> None:
        shutil.rmtree(tmp, ignore_errors=True)

    return tmp, cleanup
