"""
Ends the call as soon as the fan hangs up.

When the fan left, the agent and the realtime avatar stayed in the room for
about a minute in a 2026-10-23 local test. The avatar kept its Simli session
open all that time: it spent the plan's minutes, and because the free plan
allows one avatar session at a time, the next fan's call was refused with
429 and ran voice-only (4 of 9 back-to-back test calls).

Deleting the room disconnects every participant at once, the avatar included.
"""

import logging

from livekit import rtc
from livekit.agents import JobContext

logger = logging.getLogger(__name__)


def end_call_when_fan_leaves(ctx: JobContext) -> None:
    """Delete the room and end the job when the fan (a non-agent participant) leaves."""
    ended = False

    def on_participant_disconnected(participant: rtc.RemoteParticipant) -> None:
        nonlocal ended
        # 아바타도 agent 참가자다. 아바타가 끊긴 것은 통화를 끝낼 이유가 아니다
        if ended or participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT:
            return
        ended = True
        logger.info("Fan %s hung up; deleting the room.", participant.identity)
        ctx.delete_room()
        ctx.shutdown(reason="Fan hung up")

    ctx.room.on("participant_disconnected", on_participant_disconnected)
