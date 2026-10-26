"""
Renderers turn the trainee's speech into face frames.

A renderer takes 16 kHz mono PCM and returns one RGBA frame per 40 ms
(25 fps). Two renderers live here:

- `WebSocketRenderer` talks to a GPU render server (see
  `tools/ditto_render_server.py`) that runs a talking-head model such as
  Ditto in streaming mode. It is `continuous`: it also gets silence while the
  fan talks, so the face keeps listening naturally (blinks, small moves).
- `FakeRenderer` draws a mouth on an idle frame from the audio level. It is
  for tests and for running the call without a GPU.
"""

import asyncio
import json
from abc import ABC, abstractmethod
from io import BytesIO

import aiohttp
import numpy as np
from PIL import Image

RENDER_SAMPLE_RATE = 16_000
FPS = 25
SAMPLES_PER_FRAME = RENDER_SAMPLE_RATE // FPS  # 640 samples = 40 ms


class Renderer(ABC):
    """Audio in, face frames out."""

    #: True when the renderer should also get silence while nobody speaks,
    #: so that it keeps the face moving. False: the caller shows an idle clip.
    continuous: bool = False

    async def start(self) -> None:
        """Connect or load models. Called once before the first `render`."""

    @abstractmethod
    async def render(self, pcm: np.ndarray) -> list[np.ndarray]:
        """Frames (RGBA uint8, HxWx4) for a whole number of 40 ms of 16 kHz int16 PCM."""

    async def reset(self) -> None:
        """Forget audio that was pushed but not played (the fan interrupted)."""

    async def aclose(self) -> None:
        """Release resources."""


def rms(pcm: np.ndarray) -> float:
    """Loudness of int16 samples, 0..1."""
    if len(pcm) == 0:
        return 0.0
    return float(np.sqrt(np.mean(pcm.astype(np.float32) ** 2)) / 32768.0)


class FakeRenderer(Renderer):
    """Opens a drawn mouth on the idle frame as the audio gets louder.

    Good enough to see that audio and video stay in sync; not a face model.
    """

    def __init__(
        self, base_frame: np.ndarray, mouth_center: tuple[int, int] | None = None
    ):
        self._base = base_frame
        height, width = base_frame.shape[:2]
        self._mouth = mouth_center or (width // 2, int(height * 0.72))
        self._mouth_width = max(width // 8, 4)
        self.rendered_frames = 0

    async def render(self, pcm: np.ndarray) -> list[np.ndarray]:
        frames = []
        for start in range(0, len(pcm), SAMPLES_PER_FRAME):
            level = min(rms(pcm[start : start + SAMPLES_PER_FRAME]) * 8.0, 1.0)
            frames.append(self._draw_mouth(level))
        self.rendered_frames += len(frames)
        return frames

    def _draw_mouth(self, level: float) -> np.ndarray:
        frame = self._base.copy()
        cx, cy = self._mouth
        half_h = max(int(level * self._mouth_width * 0.6), 1)
        y0, y1 = max(cy - half_h, 0), min(cy + half_h, frame.shape[0])
        x0, x1 = max(cx - self._mouth_width, 0), min(
            cx + self._mouth_width, frame.shape[1]
        )
        frame[y0:y1, x0:x1, :3] = (40, 10, 20)
        return frame


class WebSocketRenderer(Renderer):
    """Streams audio to a render server over a WebSocket and gets JPEG frames back.

    Protocol: first a JSON text message `{"photo": <url or server path>,
    "width": W, "height": H}`; then binary int16 PCM chunks (16 kHz mono).
    The server answers each chunk with one binary JPEG per 40 ms of audio.
    A text message `{"reset": true}` drops queued audio on the server.
    """

    continuous = True

    def __init__(
        self, url: str, photo: str, *, size: tuple[int, int], layout: str | None = None
    ):
        self._url = url
        self._photo = photo
        self._size = size
        self._layout = layout
        self._session: aiohttp.ClientSession | None = None
        self._ws: aiohttp.ClientWebSocketResponse | None = None
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        self._session = aiohttp.ClientSession()
        self._ws = await self._session.ws_connect(self._url, max_msg_size=0)
        width, height = self._size
        hello: dict[str, object] = {
            "photo": self._photo,
            "width": width,
            "height": height,
        }
        if self._layout:
            hello["layout"] = self._layout
        await self._ws.send_str(json.dumps(hello))

    async def render(self, pcm: np.ndarray) -> list[np.ndarray]:
        """Send audio; get back the frames the server has ready.

        The server draws each frame only after it has 80 ms of audio past it,
        so it may answer with fewer frames than the audio holds and catch up
        on the next call. The caller keeps the unmatched audio for then.
        """
        assert self._ws is not None, "call start() first"
        async with self._lock:
            await self._ws.send_bytes(pcm.astype(np.int16).tobytes())
            header = await self._ws.receive()
            if header.type != aiohttp.WSMsgType.TEXT:
                raise ConnectionError(f"render server closed: {header.type}")
            count = int(json.loads(header.data)["frames"])
            frames = []
            for _ in range(count):
                message = await self._ws.receive()
                if message.type != aiohttp.WSMsgType.BINARY:
                    raise ConnectionError(f"render server closed: {message.type}")
                image = Image.open(BytesIO(message.data)).convert("RGBA")
                frames.append(np.asarray(image))
        return frames

    async def reset(self) -> None:
        if self._ws is not None:
            await self._ws.send_str(json.dumps({"reset": True}))

    async def aclose(self) -> None:
        if self._ws is not None:
            await self._ws.close()
        if self._session is not None:
            await self._session.close()
