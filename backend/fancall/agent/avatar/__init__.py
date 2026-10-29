"""
Self-rendered avatar: the agent draws the trainee's face itself instead of
having a hosted avatar (Simli, Anam, ...) join the room.

The agent's speech audio goes to a renderer that turns it into face frames;
the frames are published on the agent's own video track in sync with the
audio. Between replies the renderer keeps drawing the face listening, so the
trainee never freezes. See `video_generator.py` for the flow and
`renderer.py` for the renderers.
"""

from fancall.agent.avatar.idle_clip import IdleClip
from fancall.agent.avatar.renderer import FakeRenderer, Renderer, WebSocketRenderer
from fancall.agent.avatar.session import start_rendered_avatar
from fancall.agent.avatar.video_generator import RenderedVideoGenerator

__all__ = [
    "FakeRenderer",
    "IdleClip",
    "RenderedVideoGenerator",
    "Renderer",
    "WebSocketRenderer",
    "start_rendered_avatar",
]
