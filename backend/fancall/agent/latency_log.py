"""
Logs where reply latency goes in a call.

The naturalness criteria (docs/call-naturalness-criteria.md) ask the trainee to
start replying within about 1.4s of the fan finishing. A 2026-10-23 local test
measured 2.6–2.9s end to end; these lines split that into end-of-turn,
LLM first token, TTS first audio and avatar playback so each stage can be tuned.
"""

import logging
from typing import Any

from livekit.agents import AgentSession, MetricsCollectedEvent

logger = logging.getLogger(__name__)


def format_latency(metrics: Any) -> str | None:
    """One log line per latency metric, or None for metrics we don't track."""
    kind = getattr(metrics, "type", None)
    if kind == "eou_metrics":
        return (
            f"LAT end_of_turn={metrics.end_of_utterance_delay:.2f}s "
            f"transcript={metrics.transcription_delay:.2f}s"
        )
    if kind == "llm_metrics":
        return f"LAT llm_first_token={metrics.ttft:.2f}s"
    if kind == "tts_metrics":
        return f"LAT tts_first_audio={metrics.ttfb:.2f}s"
    if kind == "avatar_metrics" and metrics.playback_latency:
        return f"LAT avatar_playback={metrics.playback_latency:.2f}s"
    return None


def log_latency(session: AgentSession) -> None:
    """Log latency metrics as the session reports them."""

    def on_metrics(event: MetricsCollectedEvent) -> None:
        line = format_latency(event.metrics)
        if line:
            logger.info(line)

    session.on("metrics_collected", on_metrics)
