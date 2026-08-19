"""No-tracing compatibility layer for Alpine Private Vibe.

The complete upstream agent loop, hook manager, tool pipeline, and model backend
use these context managers.  They remain operational with inexpensive local
no-op spans, while OpenTelemetry collection and export are fully unavailable.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any


class NoopSpan:
    """Minimal span-shaped object that records nothing and never exports."""

    def set_attribute(self, key: str, value: Any) -> None:
        del key, value

    def set_attributes(self, attributes: dict[str, Any]) -> None:
        del attributes

    def set_status(self, *args: Any, **kwargs: Any) -> None:
        del args, kwargs

    def record_exception(self, error: BaseException, **kwargs: Any) -> None:
        del error, kwargs

    def is_recording(self) -> bool:
        return False


_NOOP_SPAN = NoopSpan()


def build_otel_span_exporter_config(*args: Any, **kwargs: Any) -> None:
    """Tracing export is permanently disabled in Alpine Private Vibe."""
    del args, kwargs
    return None


def setup_tracing(*args: Any, **kwargs: Any) -> None:
    """Prevent trace provider initialization and all telemetry export."""
    del args, kwargs


@asynccontextmanager
async def agent_span(*args: Any, **kwargs: Any) -> AsyncGenerator[NoopSpan]:
    del args, kwargs
    yield _NOOP_SPAN


@asynccontextmanager
async def tool_span(*args: Any, **kwargs: Any) -> AsyncGenerator[NoopSpan]:
    del args, kwargs
    yield _NOOP_SPAN


@asynccontextmanager
async def model_call_span(*args: Any, **kwargs: Any) -> AsyncGenerator[NoopSpan]:
    del args, kwargs
    yield _NOOP_SPAN


@asynccontextmanager
async def hook_span(*args: Any, **kwargs: Any) -> AsyncGenerator[NoopSpan]:
    del args, kwargs
    yield _NOOP_SPAN


def set_model_call_http_status(*args: Any, **kwargs: Any) -> None:
    del args, kwargs


def set_model_call_usage(*args: Any, **kwargs: Any) -> None:
    del args, kwargs


def set_model_call_response_metadata(*args: Any, **kwargs: Any) -> None:
    del args, kwargs


def set_tool_result(*args: Any, **kwargs: Any) -> None:
    del args, kwargs
