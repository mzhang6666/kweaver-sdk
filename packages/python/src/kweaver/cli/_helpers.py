"""Shared helpers for CLI commands."""

from __future__ import annotations

import json
import os
import sys
from functools import wraps
from typing import Any

import click

from kweaver._auth import ConfigAuth, PasswordAuth, TokenAuth
from kweaver._client import KWeaverClient
from kweaver._errors import KWeaverError, AuthenticationError, AuthorizationError, NotFoundError


def make_client() -> KWeaverClient:
    """Build an KWeaverClient from env vars or ~/.kweaver/ config.

    Priority:
      1. KWEAVER_USERNAME + KWEAVER_PASSWORD + KWEAVER_BASE_URL  → PasswordAuth (browser OAuth2, auto-refresh)
      2. KWEAVER_TOKEN + KWEAVER_BASE_URL  → TokenAuth (static, no auto-refresh)
      3. ~/.kweaver/ config  → ConfigAuth
    PasswordAuth is preferred over TokenAuth because it auto-refreshes expired tokens.
    """
    base_url = os.environ.get("KWEAVER_BASE_URL")
    bd = os.environ.get("KWEAVER_BUSINESS_DOMAIN") or "bd_public"

    username = os.environ.get("KWEAVER_USERNAME")
    password = os.environ.get("KWEAVER_PASSWORD")
    if username and password and base_url:
        auth = PasswordAuth(base_url=base_url, username=username, password=password)
        return KWeaverClient(base_url=base_url, auth=auth, business_domain=bd)

    token = os.environ.get("KWEAVER_TOKEN")
    if token and base_url:
        return KWeaverClient(base_url=base_url, auth=TokenAuth(token), business_domain=bd)

    # Default: ConfigAuth reads ~/.kweaver/
    auth = ConfigAuth()
    return KWeaverClient(auth=auth, business_domain=bd)


def pp(data: Any) -> None:
    """Pretty-print JSON data."""
    click.echo(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def error_exit(msg: str, code: int = 1) -> None:
    click.echo(f"Error: {msg}", err=True)
    sys.exit(code)


def handle_errors(fn):
    """Decorator: catch SDK errors and exit with a user-friendly message."""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except AuthenticationError as e:
            error_exit(f"认证失败: {e.message}")
        except AuthorizationError as e:
            error_exit(f"无权限: {e.message}")
        except NotFoundError as e:
            error_exit(f"未找到: {e.message}")
        except KWeaverError as e:
            error_exit(f"错误: {e.message}")
    return wrapper
