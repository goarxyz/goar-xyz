from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path

import vibe
from vibe.cli import cli
from vibe.cli.textual_ui import app
from vibe.cli.update_notifier import get_update_if_available
from vibe.core.config import VibeConfigSchema
from vibe.core.experiments.client import RemoteEvalClient
from vibe.core.tracing import build_otel_span_exporter_config


async def main() -> None:
    # Construct defaults without an API key: first launch intentionally enters
    # upstream onboarding, so normal validated construction would reject this.
    config = VibeConfigSchema.model_construct()
    assert config.enable_telemetry is False
    assert config.enable_update_checks is False
    assert config.enable_auto_update is False
    assert config.voice_mode_enabled is False
    assert config.narrator_enabled is False
    assert importlib.util.find_spec("opentelemetry") is None
    assert build_otel_span_exporter_config(None, None) is None
    assert await RemoteEvalClient.from_settings("https://example.invalid", "test").evaluate(None) is None
    assert await get_update_if_available(None) is None
    package_root = Path(vibe.__file__).resolve().parent
    assert not (package_root / "cli" / "audio_player").exists()
    assert not (package_root / "cli" / "audio_recorder").exists()
    assert not (package_root / "cli" / "transcribe").exists()
    assert cli is not None and app is not None
    print("guest privacy/TUI import validation passed")


asyncio.run(main())
