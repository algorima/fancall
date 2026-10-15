"""
Typecast text-to-speech for LiveKit agents.

Typecast has no LiveKit plugin, so this wraps its HTTP streaming endpoint
(POST /v1/text-to-speech/stream). Each sentence is one request; the agent
session splits replies into sentences through LiveKit's stream adapter.
"""

from __future__ import annotations

import httpx
from livekit.agents import (
    APIConnectionError,
    APIConnectOptions,
    APIStatusError,
    APITimeoutError,
    tts,
)
from livekit.agents.types import DEFAULT_API_CONNECT_OPTIONS

STREAM_URL = "https://api.typecast.ai/v1/text-to-speech/stream"
# Streamed WAV is 16-bit mono 32 kHz; the first chunk starts with a 44-byte header
SAMPLE_RATE = 32000
NUM_CHANNELS = 1
WAV_HEADER_BYTES = 44


class TTS(tts.TTS):
    """Typecast streaming TTS (one request per sentence)."""

    def __init__(
        self,
        *,
        api_key: str,
        voice_id: str,
        model: str = "ssfm-v30",
        language: str | None = None,
        remove_silence_ms: int | None = 100,
    ) -> None:
        super().__init__(
            capabilities=tts.TTSCapabilities(streaming=False),
            sample_rate=SAMPLE_RATE,
            num_channels=NUM_CHANNELS,
        )
        self._api_key = api_key
        self._voice_id = voice_id
        self._model = model
        self._language = language
        self._remove_silence_ms = remove_silence_ms
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(30, connect=10))

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider(self) -> str:
        return "Typecast"

    def build_payload(self, text: str) -> dict:
        """Request body for one sentence."""
        payload: dict = {
            "voice_id": self._voice_id,
            "text": text,
            "model": self._model,
            "output": {"audio_format": "wav"},
        }
        if self._model == "ssfm-v30":
            # Lets Typecast pick the emotion from the sentence itself
            payload["prompt"] = {"emotion_type": "smart"}
        if self._language:
            payload["language"] = self._language
        if self._remove_silence_ms is not None:
            payload["output"]["remove_silence_ms"] = self._remove_silence_ms
        return payload

    def synthesize(
        self,
        text: str,
        *,
        conn_options: APIConnectOptions = DEFAULT_API_CONNECT_OPTIONS,
    ) -> tts.ChunkedStream:
        return ChunkedStream(tts=self, input_text=text, conn_options=conn_options)

    async def aclose(self) -> None:
        await self._client.aclose()


class ChunkedStream(tts.ChunkedStream):
    """Streams one sentence of Typecast audio as raw PCM."""

    # `tts` is the keyword LiveKit's ChunkedStream expects
    def __init__(  # pylint: disable=redefined-outer-name
        self, *, tts: TTS, input_text: str, conn_options: APIConnectOptions
    ) -> None:
        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
        self._tts: TTS = tts

    async def _run(self, output_emitter: tts.AudioEmitter) -> None:
        tts_ = self._tts
        try:
            async with tts_._client.stream(
                "POST",
                STREAM_URL,
                headers={"X-API-KEY": tts_._api_key},
                json=tts_.build_payload(self.input_text),
            ) as response:
                if response.status_code != 200:
                    body = (await response.aread()).decode(errors="replace")
                    raise APIStatusError(
                        "Typecast TTS request failed",
                        status_code=response.status_code,
                        request_id=response.headers.get("x-request-id"),
                        body=body,
                    )
                output_emitter.initialize(
                    request_id=response.headers.get("x-request-id", ""),
                    sample_rate=SAMPLE_RATE,
                    num_channels=NUM_CHANNELS,
                    mime_type="audio/pcm",
                )
                skip = WAV_HEADER_BYTES
                async for chunk in response.aiter_bytes():
                    if skip:
                        cut = min(skip, len(chunk))
                        chunk = chunk[cut:]
                        skip -= cut
                    if chunk:
                        output_emitter.push(chunk)
                output_emitter.flush()
        except APIStatusError:
            raise
        except httpx.TimeoutException:
            raise APITimeoutError() from None
        except Exception as e:
            raise APIConnectionError() from e
