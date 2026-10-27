"""
Each spoken line sent to the host app as the call goes

The host app stores them per signed-in fan and trainee and passes them back as
`memory` on the next dispatch, so the trainee remembers the fan.
"""

import json
import logging
from typing import Any

from livekit.agents.llm import ChatMessage

from fancall.prompts import OPENING_USER_INPUT, QUIET_NUDGE_USER_INPUT

logger = logging.getLogger(__name__)

TRANSCRIPT_TOPIC = "fancall.transcript"
# Same limit as MemoryLine.text, so a stored line always fits back in
MAX_LINE_CHARS = 500
_INTERNAL_PROMPTS = {OPENING_USER_INPUT, QUIET_NUDGE_USER_INPUT}


def transcript_packet(item: Any) -> bytes | None:
    """JSON for one fan or idol line, None for anything not worth remembering."""
    if not isinstance(item, ChatMessage) or item.role not in ("user", "assistant"):
        return None
    text = " ".join((item.text_content or "").split())
    if not text or text in _INTERNAL_PROMPTS:
        return None
    record = {
        "speaker": "fan" if item.role == "user" else "idol",
        "text": text[:MAX_LINE_CHARS],
    }
    return json.dumps(record, ensure_ascii=False).encode("utf-8")


async def publish_transcript_line(room: Any, item: Any) -> None:
    """Send one line; a failure is logged and never reaches the call."""
    packet = transcript_packet(item)
    if packet is None:
        return
    try:
        await room.local_participant.publish_data(
            packet, reliable=True, topic=TRANSCRIPT_TOPIC
        )
    except Exception:  # pylint: disable=broad-exception-caught
        logger.warning("Could not send a transcript line", exc_info=True)
