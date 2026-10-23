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
from dataclasses import dataclass
from typing import Any, Protocol

from fancall.prompts import QUIET_NUDGE_INSTRUCTIONS, QUIET_NUDGE_USER_INPUT

logger = logging.getLogger(__name__)

# After the fan stops talking the speech recognizer needs up to ~0.7s to send
# the transcript (2026-10-23 test), and only then does the agent start its
# reply. Without this margin the nudge cut in on the fan's own question.
FAN_TURN_GRACE_SECONDS = 2.0


@dataclass(frozen=True)
class _Timing:
    quiet: float
    after_question: float
    fan_grace: float


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
        quiet_after_question_seconds: float | None = None,
        fan_turn_grace_seconds: float = FAN_TURN_GRACE_SECONDS,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ):
        """
        Args:
            session: Agent session to speak through
            quiet_seconds: Silence after the agent's turn before it speaks first
            max_in_row: Nudges allowed before the fan replies again (0 disables)
            quiet_after_question_seconds: Silence before speaking first when
                the agent's last line was a question (default: quiet_seconds)
            fan_turn_grace_seconds: Extra wait after the fan stops talking
            sleep: Sleep function (injected for tests)
        """
        self._session = session
        self._timing = _Timing(
            quiet=quiet_seconds,
            after_question=(
                quiet_seconds
                if quiet_after_question_seconds is None
                else quiet_after_question_seconds
            ),
            fan_grace=fan_turn_grace_seconds,
        )
        self._max_in_row = max_in_row
        self._asked = False
        self._sleep = sleep
        self._in_row = 0
        self._stopped = False
        self._agent_listening = False
        self._fan_speaking = False
        self._task: asyncio.Task[None] | None = None
        self._speech: Any = None

    def on_agent_state(self, state: str) -> None:
        """Start the quiet countdown when the agent starts listening.

        After a question the fan gets longer to answer before the agent speaks.
        """
        self._agent_listening = state == "listening"
        self._restart(
            self._timing.after_question if self._asked else self._timing.quiet
        )

    def on_agent_message(self, text: str) -> None:
        """Remember whether the agent's last line asked the fan something."""
        self._asked = text.rstrip().endswith(("?", "？"))

    def on_user_state(self, state: str) -> None:
        """Hold the countdown while the fan is speaking.

        When they stop, their turn is still on its way to the agent, so wait
        longer before speaking first; the agent's reply cancels the wait.
        """
        self._fan_speaking = state == "speaking"
        if self._fan_speaking:
            # 준비 중이던 한마디는 팬 말에 자리를 내준다
            self._interrupt_prepared_line()
        self._restart(self._timing.quiet + self._timing.fan_grace)

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

    def _restart(self, delay: float) -> None:
        self._cancel()
        if (
            self._agent_listening
            and not self._fan_speaking
            and not self._stopped
            and self._in_row < self._max_in_row
        ):
            self._task = asyncio.ensure_future(self._nudge_after_quiet(delay))

    def _cancel(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
        self._task = None

    async def _nudge_after_quiet(self, delay: float) -> None:
        await self._sleep(delay)
        self._in_row += 1
        logger.info(
            "Fan quiet for %.1fs; agent speaks first (%d/%d)",
            delay,
            self._in_row,
            self._max_in_row,
        )
        self._speech = self._session.generate_reply(
            user_input=QUIET_NUDGE_USER_INPUT, instructions=QUIET_NUDGE_INSTRUCTIONS
        )

    def _interrupt_prepared_line(self) -> None:
        speech = self._speech
        if speech is not None and not speech.done():
            speech.interrupt()
