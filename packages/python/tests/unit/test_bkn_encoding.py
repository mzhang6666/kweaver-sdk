"""Tests for BKN .bkn file encoding normalization."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

import pytest

from kweaver.cli.bkn_encoding import (
    normalize_bkn_file_bytes,
    prepare_bkn_directory_for_import,
)


def test_normalize_utf8_passthrough_detect() -> None:
    raw = "---\ntype: network\nid: x\nname: 测试\n---\n# 标题\n".encode("utf-8")
    out = normalize_bkn_file_bytes(
        raw,
        detect_encoding=True,
        source_encoding=None,
        file_label="n.bkn",
    )
    assert out.decode("utf-8") == raw.decode("utf-8")


def test_normalize_utf8_bom() -> None:
    body = "---\nid: x\n---\n".encode("utf-8")
    raw = b"\xef\xbb\xbf" + body
    out = normalize_bkn_file_bytes(
        raw,
        detect_encoding=True,
        source_encoding=None,
        file_label="n.bkn",
    )
    assert out == body


def test_normalize_source_encoding_gb18030() -> None:
    text = "---\ntype: network\nid: x\nname: 测试\n---\n"
    raw = text.encode("gb18030")
    out = normalize_bkn_file_bytes(
        raw,
        detect_encoding=False,
        source_encoding="gb18030",
        file_label="n.bkn",
    )
    assert out.decode("utf-8") == text


def test_normalize_no_detect_invalid_utf8_raises() -> None:
    with pytest.raises(UnicodeDecodeError):
        normalize_bkn_file_bytes(
            b"\xff\xfe\xfd",
            detect_encoding=False,
            source_encoding=None,
            file_label="n.bkn",
        )


def test_prepare_skips_temp_when_no_detect_no_source(tmp_path: Path) -> None:
    d, cleanup = prepare_bkn_directory_for_import(
        tmp_path,
        detect_encoding=False,
        source_encoding=None,
    )
    assert d == tmp_path.resolve()
    cleanup()


def test_prepare_copies_tree_with_source_encoding_gb18030(tmp_path: Path) -> None:
    """Forced --source-encoding path copies tree and rewrites .bkn as UTF-8."""
    text = "---\ntype: network\nid: net\nname: 网络\n---\n# T\n"
    net = tmp_path / "network.bkn"
    net.write_bytes(text.encode("gb18030"))

    work, cleanup = prepare_bkn_directory_for_import(
        tmp_path,
        detect_encoding=False,
        source_encoding="gb18030",
    )
    try:
        out = (work / "network.bkn").read_bytes()
        assert out.decode("utf-8") == text
    finally:
        cleanup()


def test_normalize_detect_gb18030_longer_content() -> None:
    """Auto-detection should succeed on enough non-ASCII GB18030 bytes."""
    text = (
        "---\ntype: network\nid: net\nname: 网络描述示例\n---\n"
        "# 标题\n正文内容 " * 20
        + "\n"
    )
    raw = text.encode("gb18030")
    out = normalize_bkn_file_bytes(
        raw,
        detect_encoding=True,
        source_encoding=None,
        file_label="network.bkn",
    )
    assert out.decode("utf-8") == text

