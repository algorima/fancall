"""
Outbound phone call over LiveKit SIP.

The agent places the call itself and waits until the fan picks up, so the
"여보세요" greeting is not spoken into an empty, still-ringing room.
"""

import logging
from typing import Protocol

from livekit import api
from livekit.protocol.sip import CreateSIPParticipantRequest

logger = logging.getLogger(__name__)

PHONE_PARTICIPANT_IDENTITY = "phone-fan"


class SipParticipantCreator(Protocol):
    """Part of livekit SipService the dialer uses."""

    async def create_sip_participant(
        self, create: CreateSIPParticipantRequest
    ) -> object: ...


async def dial_phone(
    sip: SipParticipantCreator,
    room_name: str,
    trunk_id: str,
    phone_number: str,
) -> bool:
    """
    Call a phone number into the room and wait until it is answered.

    Args:
        sip: LiveKit SIP service (ctx.api.sip in the worker)
        room_name: Room the phone participant joins
        trunk_id: LiveKit SIP outbound trunk ID
        phone_number: E.164 phone number to call

    Returns:
        True if the fan answered, False if the call failed or was not answered
    """
    try:
        await sip.create_sip_participant(
            CreateSIPParticipantRequest(
                room_name=room_name,
                sip_trunk_id=trunk_id,
                sip_call_to=phone_number,
                participant_identity=PHONE_PARTICIPANT_IDENTITY,
                wait_until_answered=True,
            )
        )
    except api.TwirpError as e:
        # 안 받음·거절·통화 중은 예상된 실패다. 번호는 로그에 남기지 않는다
        logger.warning(
            "Phone call was not answered: %s (SIP status %s)",
            e.message,
            (e.metadata or {}).get("sip_status_code"),
        )
        return False

    return True
