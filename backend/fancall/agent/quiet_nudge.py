"""
Keeps a video call from going quiet.

The video-call prompt lets the fan lead, because fans at real 영통팬싸 come
with things to say. Fans trying AIdol for the first time often do not: in a
2026-10-23 local test the trainee answered in about three seconds and then sat
silent until the next typed message. When the fan has been quiet for a while
after the trainee finished speaking, the trainee says something first, the way
an idol fills a pause on a real call.

The nudger only asks for a reply. It never pleads or guilt-trips the fan into
staying; QUIET_NUDGE_INSTRUCTIONS forbids that.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from fancall.prompts import QUIET_NUDGE_INSTRUCTIONS, QUIET_NUDGE_USER_INPUT

logger = logging.getLogger(__name__)


class NudgeSession(Protocol):
    """Part of livekit AgentSession the nudger uses."""

    def generate_reply(self, *, user_input: str, instructions: str) -> Any: ...


class QuietNudger:
    """Asks the agent to speak when the fan stays quiet after the agent's turn."""

    def __init__(
        self,
        session: NudgeSession,
        *,
        quiet_seconds: float,
        max_in_row: int,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        """
        Args:
            session: Agent session to speak through
            quiet_seconds: Silence after the agent's turn before it speaks first
            max_in_row: Nudges allowed before the fan replies again (0 disables)
            sleep: Sleep function (injected for tests)
        """
        self._session = session
        self._quiet_seconds = quiet_seconds
        self._max_in_row = max_in_row
        self._sleep = sleep
        self._in_row = 0
        self._stopped = False
        self._task: asyncio.Task[None] | None = None

    def on_agent_state(self, state: str) -> None:
        """Start the quiet countdown when the agent starts listening."""
        self._cancel()
        if (
            state == "listening"
            and not self._stopped
            and self._in_row < self._max_in_row
        ):
            self._task = asyncio.ensure_future(self._nudge_after_quiet())

    def on_user_message(self, text: str) -> None:
        """A fan message cancels the countdown and resets the limit."""
        # 한마디를 부를 때 넣는 팬 쪽 지문도 user 메시지로 기록되므로 팬 말로 치지 않는다
        if text == QUIET_NUDGE_USER_INPUT:
            return
        self._in_row = 0
        self._cancel()

    def stop(self) -> None:
        """Stop nudging, e.g. once the call starts wrapping up."""
        self._stopped = True
        self._cancel()

    def _cancel(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
        self._task = None

    async def _nudge_after_quiet(self) -> None:
        await self._sleep(self._quiet_seconds)
        self._in_row += 1
        logger.info(
            "Fan quiet for %.0fs; agent speaks first (%d/%d)",
            self._quiet_seconds,
            self._in_row,
            self._max_in_row,
        )
        self._session.generate_reply(
            user_input=QUIET_NUDGE_USER_INPUT, instructions=QUIET_NUDGE_INSTRUCTIONS
        )
