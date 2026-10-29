"""LiveKit Cloud TTS built from settings: one voice string plus optional language and style."""

from typing import Any

from livekit.agents import inference

from fancall.settings import FancallModelSettings


def cloud_tts_kwargs(model_settings: FancallModelSettings) -> dict[str, Any]:
    """inference.TTS keyword arguments; empty settings are left out so provider defaults apply."""
    kwargs: dict[str, Any] = {"model": model_settings.tts_model}
    if model_settings.tts_language:
        kwargs["language"] = model_settings.tts_language
    instructions = model_settings.tts_instructions.strip()
    if instructions:
        kwargs["extra_kwargs"] = {"instructions": instructions}
    return kwargs


def build_cloud_tts(model_settings: FancallModelSettings) -> inference.TTS:
    """A fresh Cloud TTS connection (the call and the quick reactions each need their own)."""
    return inference.TTS(**cloud_tts_kwargs(model_settings))
