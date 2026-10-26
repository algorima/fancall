"""
GPU render server for the self-rendered avatar: streams a talking face.

Runs next to a checkout of Ditto (https://github.com/antgroup/ditto-talkinghead,
Apache-2.0) on a machine with an NVIDIA GPU. The agent's `WebSocketRenderer`
connects, sends 16 kHz int16 PCM, and gets back one JPEG per 40 ms.

    python tools/ditto_render_server.py --ditto /path/to/ditto-talkinghead \
        --data-root checkpoints/ditto_trt_Ampere_Plus \
        --cfg checkpoints/ditto_cfg/v0.4_hubert_cfg_trt_online.pkl --port 8765

Protocol (one WebSocket per call):
    client → text   {"photo": "<path>", "width": W, "height": H,
                     "layout": {...}}        # see `Layout`; optional
    client → binary int16 PCM, any multiple of 640 samples (40 ms)
    server → text   {"frames": N} then N binary JPEG frames
    client → text   {"reset": true}           # drop audio not yet rendered

Ditto needs 80 ms of audio after a frame to draw it, so frames come back two
frames behind the audio; the agent pairs them with the audio it still holds,
and keeps sending silence between replies so the face keeps listening.
"""

import argparse
import asyncio
import json
import logging
import os
import queue
import sys
import threading
from dataclasses import dataclass
from io import BytesIO

import numpy as np
from aiohttp import WSMsgType, web
from PIL import Image

logger = logging.getLogger("render")

SAMPLE_RATE = 16_000
FRAME = SAMPLE_RATE // 25  # 640 samples
CHUNK = (3, 5, 2)  # Ditto hubert context: 3 frames before, 5 to render, 2 after
WINDOW = sum(CHUNK) * FRAME + 80  # 6480 samples per run_chunk
LOOKAHEAD = CHUNK[2]


@dataclass
class Layout:
    """Where the rendered face goes on the wide call photo (see call_look.py)."""

    wide: np.ndarray  # HxWx3 RGB
    affine: np.ndarray  # 2x3, face video → wide photo
    mask: np.ndarray  # HxWx1 float 0..1

    @classmethod
    def from_json(cls, spec: dict) -> "Layout":
        """Build from {"wide": path, "affine": [[..],[..]], "ellipse": {cx,cy,ax,ay_up,ay_down}}."""
        import cv2  # pylint: disable=import-outside-toplevel,import-error  # pyright: ignore[reportMissingImports]

        wide = np.asarray(Image.open(spec["wide"]).convert("RGB"))
        height, width = wide.shape[:2]
        e = spec["ellipse"]
        yy, xx = np.mgrid[0:height, 0:width]
        ay = np.where(yy < e["cy"], e["ay_up"], e["ay_down"])
        d = np.sqrt(((xx - e["cx"]) / e["ax"]) ** 2 + ((yy - e["cy"]) / ay) ** 2)
        mask = np.clip((1.0 - d) / 0.35, 0, 1).astype(np.float32)
        mask = cv2.GaussianBlur(mask, (0, 0), 6)[..., None]
        return cls(wide, np.asarray(spec["affine"], dtype=np.float32), mask)

    def apply(self, face_rgb: np.ndarray) -> np.ndarray:
        """Paste one face frame onto the wide photo."""
        import cv2  # pylint: disable=import-outside-toplevel,import-error  # pyright: ignore[reportMissingImports]

        height, width = self.wide.shape[:2]
        warped = cv2.warpAffine(
            face_rgb, self.affine, (width, height), borderMode=cv2.BORDER_REFLECT
        )
        out = (
            self.wide.astype(np.float32) * (1 - self.mask)
            + warped.astype(np.float32) * self.mask
        )
        return out.astype(np.uint8)


class FrameQueue:
    """Stands in for Ditto's video writer: frames go to a queue instead of a file."""

    def __init__(self) -> None:
        self.frames: "queue.Queue[np.ndarray | None]" = queue.Queue()

    def __call__(self, img: np.ndarray, fmt: str = "bgr") -> None:
        self.frames.put(img[..., ::-1] if fmt == "bgr" else img)

    def close(self) -> None:
        self.frames.put(None)


class DittoStream:
    """One Ditto streaming session for one photo."""

    def __init__(self, sdk, photo: str, max_size: int):
        self._sdk = sdk
        self._frames = FrameQueue()
        self._audio: np.ndarray = np.zeros(
            CHUNK[0] * FRAME, dtype=np.float32
        )  # 3 frames of context
        self._rendered_upto = 0  # samples of real audio turned into frames
        sdk.setup(photo, "/tmp/ditto_stream.mp4", online_mode=True, max_size=max_size)
        sdk.setup_Nd(N_d=-1)
        sdk.writer = self._frames
        sdk.writer_pbar.disable = True
        # Warm up: the first forward pass takes seconds (CUDA init, kernel
        # selection). Render one second of silence now so the call does not wait.
        self.push(np.zeros(SAMPLE_RATE, dtype=np.int16))
        self.take(10**6, wait=20.0)

    def push(self, pcm_int16: np.ndarray) -> int:
        """Add audio; render every whole 5-frame window that now has its lookahead."""
        self._audio = np.concatenate(
            [self._audio, pcm_int16.astype(np.float32) / 32768.0]
        )
        produced = 0
        step = CHUNK[1] * FRAME
        while len(self._audio) - self._rendered_upto >= WINDOW:
            self._sdk.run_chunk(
                self._audio[self._rendered_upto : self._rendered_upto + WINDOW], CHUNK
            )
            self._rendered_upto += step
            produced += CHUNK[1]
        return produced

    def take(self, count: int, wait: float) -> list[np.ndarray]:
        """Up to `count` rendered RGB frames: wait `wait` seconds for the first, then whatever is ready.

        Ditto emits frames a few chunks after the audio (model context), so a
        chunk may yield none now and several later; the agent copes with that.
        """
        out: list[np.ndarray] = []
        try:
            first = self._frames.frames.get(timeout=wait)
        except queue.Empty:
            return out
        if first is None:
            return out
        out.append(first)
        while len(out) < count:
            try:
                frame = self._frames.frames.get_nowait()
            except queue.Empty:
                break
            if frame is None:
                break
            out.append(frame)
        return out

    def reset(self) -> None:
        """Forget audio that has not been rendered yet."""
        keep = CHUNK[0] * FRAME
        self._audio = self._audio[
            max(self._rendered_upto - keep, 0) : self._rendered_upto
        ]
        self._rendered_upto = len(self._audio)

    def close(self) -> None:
        self._sdk.close()


def _jpeg(rgb: np.ndarray, size: tuple[int, int] | None, quality: int) -> bytes:
    image = Image.fromarray(rgb)
    if size and image.size != size:
        image = image.resize(size, Image.Resampling.BILINEAR)
    buf = BytesIO()
    image.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


class Server:
    """Serves one Ditto stream per WebSocket connection (one GPU: one call at a time)."""

    def __init__(self, sdk_factory, max_size: int, quality: int):
        self._sdk_factory = sdk_factory
        self._max_size = max_size
        self._quality = quality
        self._lock = threading.Lock()

    async def handle(self, request: web.Request) -> web.WebSocketResponse:
        """One call."""
        ws = web.WebSocketResponse(max_msg_size=0)
        await ws.prepare(request)
        first = await ws.receive_json()
        size = (int(first["width"]), int(first["height"])) if "width" in first else None
        layout = None
        if first.get("layout"):
            spec = first["layout"]
            if isinstance(spec, str):  # a path on this machine
                with open(spec, encoding="utf-8") as f:
                    spec = json.load(f)
            layout = Layout.from_json(spec)
        loop = asyncio.get_running_loop()
        stream = await loop.run_in_executor(None, self._open, first["photo"])
        pending = 0  # frames rendered on the GPU but not yet sent
        try:
            async for message in ws:
                if message.type == WSMsgType.TEXT:
                    if json.loads(message.data).get("reset"):
                        stream.reset()
                    continue
                if message.type != WSMsgType.BINARY:
                    break
                pcm = np.frombuffer(message.data, dtype=np.int16)
                pending += await loop.run_in_executor(None, stream.push, pcm)
                frames = await loop.run_in_executor(None, stream.take, pending, 0.03)
                pending -= len(frames)
                if layout is not None:
                    frames = [layout.apply(f) for f in frames]
                await ws.send_str(json.dumps({"frames": len(frames)}))
                for frame in frames:
                    await ws.send_bytes(_jpeg(frame, size, self._quality))
        finally:
            await loop.run_in_executor(None, stream.close)
            self._lock.release()
        return ws

    def _open(self, photo: str) -> DittoStream:
        if not self._lock.acquire(timeout=1):  # pylint: disable=consider-using-with
            raise web.HTTPServiceUnavailable(text="a call is already being rendered")
        return DittoStream(self._sdk_factory(), photo, self._max_size)


def main() -> None:
    """Start the server."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--ditto", required=True, help="path to the ditto-talkinghead checkout"
    )
    parser.add_argument("--data-root", required=True)
    parser.add_argument(
        "--cfg", required=True, help="an *_online.pkl config for streaming"
    )
    parser.add_argument(
        "--max-size", type=int, default=720, help="longest side the model renders"
    )
    parser.add_argument(
        "--quality", type=int, default=85, help="JPEG quality sent to the agent"
    )
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)

    sys.path.insert(0, os.path.abspath(args.ditto))
    os.chdir(args.ditto)
    # pylint: disable-next=import-outside-toplevel,import-error
    from stream_pipeline_online import StreamSDK  # pyright: ignore

    sdk = StreamSDK(args.cfg, args.data_root)  # models load once; setup() per call
    server = Server(lambda: sdk, args.max_size, args.quality)
    app = web.Application()
    app.router.add_get("/", server.handle)
    web.run_app(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
