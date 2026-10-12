"""
Call timer that ends a video call the way real idol fan calls end.

Real fan calls end on a hard clock, and the idol says goodbye just before it
("가야 된대 미안해 시간이 없어~"). The timer works in two steps:

1. wrap_up_lead_seconds before the end, the agent stops opening new topics.
2. closing_lead_seconds before the end, the agent cuts in with a goodbye that
   the fan cannot interrupt, then the timer waits for it to finish playing.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any, Protocol

from fancall.prompts import CLOSING_INSTRUCTIONS, WRAP_UP_INSTRUCTIONS
from fancall.settings import FancallCallSettings

logger = logging.getLogger(__name__)


class SpeechPlayout(Protocol):
    """Part of livekit SpeechHandle the timer uses."""

    async def wait_for_playout(self) -> None: ...


class CallSession(Protocol):
    """Part of livekit AgentSession the timer uses."""

    def interrupt(self) -> Any: ...

    def generate_reply(
        self, *, instructions: str, allow_interruptions: bool
    ) -> SpeechPlayout: ...


class InstructableAgent(Protocol):
    """Part of livekit Agent the timer uses."""

    async def update_instructions(self, instructions: str) -> None: ...


async def run_call_timer(
    session: CallSession,
    agent: InstructableAgent,
    base_instructions: str,
    settings: FancallCallSettings,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> None:
    """
    Run the call clock from session start until the goodbye has played.

    Args:
        session: Agent session to speak through
        agent: Agent whose instructions get the wrap-up hint
        base_instructions: Instructions the agent started with
        settings: Call timing settings
        sleep: Sleep function (injected for tests)
    """
    await sleep(settings.call_duration_seconds - settings.wrap_up_lead_seconds)
    logger.info("Call wrap-up: %.0fs left", settings.wrap_up_lead_seconds)
    await agent.update_instructions(base_instructions + "\n\n" + WRAP_UP_INSTRUCTIONS)

    await sleep(settings.wrap_up_lead_seconds - settings.closing_lead_seconds)
    logger.info("Call closing: %.0fs left", settings.closing_lead_seconds)
    # 실제 영통처럼 하던 말을 끊고 작별 인사로 넘어간다
    session.interrupt()
    goodbye = session.generate_reply(
        instructions=CLOSING_INSTRUCTIONS, allow_interruptions=False
    )

    try:
        await asyncio.wait_for(
            goodbye.wait_for_playout(),
            timeout=settings.closing_lead_seconds + settings.closing_grace_seconds,
        )
    except asyncio.TimeoutError:
        logger.warning("Goodbye did not finish before the grace period ended.")
