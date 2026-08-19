"""No-experiment session hooks for Alpine Private Vibe.

The upstream runtime keeps these entry points in its session lifecycle.  They
are deliberately inert here: no identity/account lookup, experiment cache,
platform attribute construction, or remote evaluation is permitted.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from vibe.core.experiments.manager import ExperimentManager
    from vibe.core.session.session_logger import SessionLogger
    from vibe.core.telemetry.types import LaunchContext
    from vibe.core.config import VibeConfigSchema


async def initialize_experiments(
    *,
    config: VibeConfigSchema,
    manager: ExperimentManager,
    session_logger: SessionLogger,
    launch_context: LaunchContext | None,
    **_kwargs: object,
) -> bool:
    del config, manager, session_logger, launch_context
    return False


async def hydrate_experiments_from_session(
    *,
    config: VibeConfigSchema,
    manager: ExperimentManager,
    session_logger: SessionLogger,
) -> bool:
    del config, manager, session_logger
    return False
