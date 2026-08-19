"""No-network experiment compatibility client for Alpine Private Vibe."""

from __future__ import annotations

from vibe.core.experiments.models import EvalResponse, ExperimentAttributes


class RemoteEvalClient:
    """Retained upstream interface; remote evaluation is permanently disabled."""

    def __init__(self, *, url: str | None = None) -> None:
        del url

    @classmethod
    def from_settings(cls, api_host: str, client_key: str) -> RemoteEvalClient:
        del api_host, client_key
        return cls()

    async def evaluate(self, attributes: ExperimentAttributes) -> EvalResponse | None:
        del attributes
        return None

    async def aclose(self) -> None:
        return None
