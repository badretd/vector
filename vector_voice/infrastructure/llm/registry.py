"""Registry that maps provider ids to provider instances."""
from __future__ import annotations

from vector_voice.domain.ports import LlmProviderPort


class LlmProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, LlmProviderPort] = {}

    def register(self, provider: LlmProviderPort) -> None:
        self._providers[provider.provider_id] = provider

    def get(self, provider_id: str) -> LlmProviderPort | None:
        return self._providers.get(provider_id)

    def default(self) -> LlmProviderPort:
        if not self._providers:
            raise RuntimeError("No LLM providers registered")
        # Preserve the original single-provider behaviour.
        return next(iter(self._providers.values()))

    def ids(self) -> list[str]:
        return list(self._providers.keys())