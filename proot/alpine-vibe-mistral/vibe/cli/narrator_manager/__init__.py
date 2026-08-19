"""Port-only narrator interface for Alpine Private Vibe.

Concrete playback and text-to-speech support is intentionally absent.  The
full Textual UI uses the retained protocol and permanent no-op manager instead.
"""

from vibe.cli.narrator_manager.narrator_manager_port import (
    NarratorManagerListener,
    NarratorManagerPort,
    NarratorState,
)

__all__ = ["NarratorManagerListener", "NarratorManagerPort", "NarratorState"]
