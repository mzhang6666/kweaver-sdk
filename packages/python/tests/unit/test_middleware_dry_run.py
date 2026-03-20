"""Tests for DryRun middleware."""
from __future__ import annotations

import pytest
from kweaver._errors import DryRunIntercepted, KWeaverError


def test_dry_run_intercepted_is_kweaver_error():
    exc = DryRunIntercepted(method="POST", url="/api/test", body={"name": "foo"})
    assert isinstance(exc, KWeaverError)
    assert exc.method == "POST"
    assert exc.url == "/api/test"
    assert exc.body == {"name": "foo"}
    assert "[DRY RUN]" in str(exc)


def test_dry_run_intercepted_no_body():
    exc = DryRunIntercepted(method="DELETE", url="/api/test/1")
    assert exc.body is None
    assert "DELETE" in str(exc)
