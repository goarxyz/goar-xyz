"""Privacy-first compatibility boundary for upstream Sentry integration.

The Alpine Private Vibe edition intentionally contains no crash-reporting client.
This module preserves the upstream public API so the full Mistral Vibe TUI, ACP
entrypoint, and app-server exception paths retain their normal local handling
without importing or contacting Sentry.
"""

from collections.abc import Mapping
from enum import StrEnum, auto
from typing import Any


class SentryTarget(StrEnum):
    """Retained only for source compatibility with upstream entrypoints."""

    CLI = auto()
    ACP = auto()

    @property
    def dsn(self) -> None:
        """Crash reporting is intentionally unavailable in this edition."""
        return None

    @property
    def server_name(self) -> str:
        return "goar-alpine-private-vibe"


def scrub_paths(value: Any) -> Any:
    """Return locally handled values unchanged; nothing is sent off-device."""
    return value


def init_sentry(
    *,
    enabled: bool,
    headless: bool,
    tags: Mapping[str, str],
    target: SentryTarget = SentryTarget.CLI,
) -> bool:
    """Deliberately disable all crash-reporting initialization."""
    del enabled, headless, tags, target
    return False


def capture_sentry_exception(
    error: BaseException,
    *,
    fatal: bool,
    tags: dict[str, str] | None = None,
    extras: dict[str, Any] | None = None,
) -> None:
    """Deliberately drop reportable exception data on-device."""
    del error, fatal, tags, extras


__all__ = ["SentryTarget", "capture_sentry_exception", "init_sentry", "scrub_paths"]
