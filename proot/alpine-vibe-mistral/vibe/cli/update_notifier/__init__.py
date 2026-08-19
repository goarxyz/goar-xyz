"""Private, no-network compatibility boundary for upstream update integration.

Alpine Private Vibe neither checks registries nor reads release feeds, stores
update caches, displays whats-new content, or performs automatic updates.  The
small API below keeps the complete upstream terminal UI import-compatible until
its ordinary startup paths are reached.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Any, Protocol


@dataclass(frozen=True)
class Update:
    version: str = ""
    url: str | None = None
    message: str | None = None


@dataclass(frozen=True)
class UpdateAvailability:
    update: Update | None = None
    is_available: bool = False


@dataclass(frozen=True)
class UpdateCache:
    update: Update | None = None
    checked_at: float | None = None


class UpdateGatewayCause(StrEnum):
    DISABLED = auto()


class UpdateGatewayError(Exception):
    pass


class UpdateError(Exception):
    pass


DEFAULT_GATEWAY_MESSAGES: dict[UpdateGatewayCause, str] = {
    UpdateGatewayCause.DISABLED: "Update checks are disabled in Alpine Private Vibe."
}


class UpdateGateway(Protocol):
    async def get_latest_update(self, current_version: str) -> Update | None: ...


class UpdateCacheRepository(Protocol):
    async def get(self) -> UpdateCache | None: ...

    async def save(self, cache: UpdateCache) -> None: ...


class _DisabledUpdateGateway:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        del args, kwargs

    async def get_latest_update(self, current_version: str) -> None:
        del current_version
        return None


class PyPIUpdateGateway(_DisabledUpdateGateway):
    """Retained name; registry access is permanently disabled."""


class GitHubUpdateGateway(_DisabledUpdateGateway):
    """Retained name; release-feed access is permanently disabled."""


class FileSystemUpdateCacheRepository:
    """No-op local repository; this edition persists no update metadata."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        del args, kwargs

    async def get(self) -> None:
        return None

    async def save(self, cache: UpdateCache) -> None:
        del cache


async def get_update_if_available(*args: Any, **kwargs: Any) -> None:
    del args, kwargs
    return None


async def get_pending_update_from_cache(*args: Any, **kwargs: Any) -> None:
    del args, kwargs
    return None


async def mark_update_as_dismissed(*args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return False


async def should_show_whats_new(*args: Any, **kwargs: Any) -> bool:
    del args, kwargs
    return False


async def mark_version_as_seen(*args: Any, **kwargs: Any) -> None:
    del args, kwargs


def load_whats_new_content() -> None:
    return None


__all__ = [
    "DEFAULT_GATEWAY_MESSAGES",
    "FileSystemUpdateCacheRepository",
    "GitHubUpdateGateway",
    "PyPIUpdateGateway",
    "Update",
    "UpdateAvailability",
    "UpdateCache",
    "UpdateCacheRepository",
    "UpdateError",
    "UpdateGateway",
    "UpdateGatewayCause",
    "UpdateGatewayError",
    "get_pending_update_from_cache",
    "get_update_if_available",
    "load_whats_new_content",
    "mark_update_as_dismissed",
    "mark_version_as_seen",
    "should_show_whats_new",
]
