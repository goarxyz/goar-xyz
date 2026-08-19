"""No-network telemetry compatibility layer for the Alpine Private Vibe edition.

This private fork retains upstream call sites so the complete Mistral Vibe TUI,
agent loop, ACP surface, session persistence, and tool workflow remain intact.
All analytics methods intentionally discard their inputs locally and never create
an HTTP client, task, cache, or outbound request.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from vibe.core.config import ProviderConfig, VibeConfigSchema
from vibe.core.telemetry.types import LaunchContext


def get_mistral_provider_and_api_key(
    config: VibeConfigSchema,
) -> tuple[ProviderConfig, str] | None:
    """Never resolve credentials for analytics or experiment transport."""
    del config
    return None


class TelemetryClient:
    """API-compatible, permanently disabled telemetry client."""

    def __init__(
        self,
        config_getter: Callable[[], VibeConfigSchema],
        session_id_getter: Callable[[], str | None] | None = None,
        parent_session_id_getter: Callable[[], str | None] | None = None,
        launch_context: LaunchContext | None = None,
        experiments_getter: Callable[[], dict[str, str]] | None = None,
        user_plan_getter: Callable[[], str | None] | None = None,
    ) -> None:
        del (
            config_getter,
            session_id_getter,
            parent_session_id_getter,
            launch_context,
            experiments_getter,
            user_plan_getter,
        )
        self.last_correlation_id: str | None = None

    def is_active(self) -> bool:
        return False

    @property
    def session_id(self) -> None:
        return None

    @property
    def parent_session_id(self) -> None:
        return None

    @property
    def user_plan(self) -> None:
        return None

    def build_client_event_metadata(self) -> dict[str, object]:
        return {}

    def send_telemetry_event(
        self,
        event_name: str,
        properties: dict[str, Any],
        *,
        correlation_id: str | None = None,
    ) -> None:
        del event_name, properties, correlation_id

    async def aclose(self) -> None:
        return None

    def send_tool_call_finished(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def send_user_copied_text(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def send_user_cancelled_action(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def send_auto_compact_triggered(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def send_compaction_failed(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def send_slash_command_used(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def send_new_session(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def send_session_closed(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def send_admin_config_applied(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def send_onboarding_api_key_added(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def send_request_sent(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def send_ready(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def send_at_mention_inserted(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def send_user_rating_feedback(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def send_teleport_completed(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def send_teleport_failed(self, *args: object, **kwargs: object) -> None:
        del args, kwargs

    def send_remote_project_configured(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
