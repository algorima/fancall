"""
A short clip of the trainee listening (blinking, small head moves), played in
a loop while nobody speaks for them.

The clip is a directory of JPEG frames named in order (`00001.jpg`, ...) with a
`clip.json` holding the frame rate, made offline with ffmpeg from a video the
face model rendered for silence. It loops back and forth (ping-pong) so the
loop point does not jump.
"""

import json
from pathlib import Path

import numpy as np
from PIL import Image


class IdleClip:
    """Frames of the trainee listening, looped without a visible seam."""

    def __init__(self, frames: list[np.ndarray], fps: float):
        if not frames:
            raise ValueError("an idle clip needs at least one frame")
        self._frames = frames
        self._fps = fps

    @classmethod
    def load(
        cls, directory: str | Path, size: tuple[int, int] | None = None
    ) -> "IdleClip":
        """Load `*.jpg` frames (sorted by name) and `clip.json` from a directory."""
        directory = Path(directory)
        meta = json.loads((directory / "clip.json").read_text(encoding="utf-8"))
        frames = []
        for path in sorted(directory.glob("*.jpg")):
            image = Image.open(path).convert("RGBA")
            if size and image.size != size:
                image = image.resize(size, Image.Resampling.BILINEAR)
            frames.append(np.asarray(image))
        return cls(frames, float(meta["fps"]))

    @classmethod
    def still(cls, frame: np.ndarray, fps: float = 25.0) -> "IdleClip":
        """A clip of one frame, for a face that does not move while listening."""
        return cls([frame], fps)

    @property
    def fps(self) -> float:
        """Frame rate the clip was rendered at."""
        return self._fps

    @property
    def size(self) -> tuple[int, int]:
        """(width, height) of the frames."""
        height, width = self._frames[0].shape[:2]
        return width, height

    def frame(self, index: int) -> np.ndarray:
        """The frame to show at the given frame count since the clip started.

        Plays forward to the end, then backward to the start, and so on.
        """
        count = len(self._frames)
        if count == 1:
            return self._frames[0]
        period = 2 * (count - 1)
        position = index % period
        if position >= count:
            position = period - position
        return self._frames[position]
