"""The registry of transcription providers."""
from __future__ import annotations

from providers.base import (CancelCallback, ProgressCallback, ProviderCapabilities, ProviderError, ProviderInfo,
                            TranscriptionProvider, emit_progress, feature_state, group_by_speaker, speaker_label,
                            whole_file_segment)
from providers.deepgram import DeepgramProvider
from providers.gladia import GladiaProvider
from providers.openai_compatible import OpenAICompatibleProvider
from providers.openai_diarize import OpenAIDiarizeProvider
from providers.soniox import SonioxProvider

DEFAULT_PROVIDER = GladiaProvider.info.key

# This order is also the order they appear in the Settings picker.
PROVIDERS: dict[str, type[TranscriptionProvider]] = {
    provider.info.key: provider
    for provider in (GladiaProvider, SonioxProvider, DeepgramProvider, OpenAIDiarizeProvider, OpenAICompatibleProvider)
}

__all__ = ["CancelCallback", "DEFAULT_PROVIDER", "DeepgramProvider", "GladiaProvider", "OpenAICompatibleProvider",
           "OpenAIDiarizeProvider", "PROVIDERS", "ProgressCallback", "ProviderCapabilities", "ProviderError",
           "ProviderInfo", "SonioxProvider", "TranscriptionProvider", "emit_progress", "feature_state",
           "group_by_speaker", "provider_capabilities", "provider_choices", "provider_info", "speaker_label",
           "whole_file_segment"]


def provider_info(key: str) -> ProviderInfo:
    return PROVIDERS.get(key, PROVIDERS[DEFAULT_PROVIDER]).info


def provider_capabilities(key: str) -> ProviderCapabilities:
    return provider_info(key).capabilities


def provider_choices() -> list[ProviderInfo]:
    return [provider.info for provider in PROVIDERS.values()]
