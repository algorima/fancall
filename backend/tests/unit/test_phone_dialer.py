"""
Unit tests for the outbound phone dialer
"""

import unittest

from livekit import api
from livekit.protocol.sip import CreateSIPParticipantRequest

from fancall.agent.phone_dialer import PHONE_PARTICIPANT_IDENTITY, dial_phone


class FakeSip:
    """Records SIP participant requests and optionally fails them."""

    def __init__(self, error: api.TwirpError | None = None):
        self.requests: list[CreateSIPParticipantRequest] = []
        self.error = error

    async def create_sip_participant(
        self, create: CreateSIPParticipantRequest
    ) -> object:
        self.requests.append(create)
        if self.error:
            raise self.error
        return object()


class TestDialPhone(unittest.IsolatedAsyncioTestCase):
    """Tests for dial_phone"""

    async def test_answered_call_returns_true(self):
        """Test an answered call reports success"""
        sip = FakeSip()

        answered = await dial_phone(sip, "room-1", "ST_trunk", "+821012345678")

        self.assertTrue(answered)

    async def test_request_waits_until_answered(self):
        """Test the call blocks until pickup so the greeting is not lost"""
        sip = FakeSip()

        await dial_phone(sip, "room-1", "ST_trunk", "+821012345678")

        request = sip.requests[0]
        self.assertEqual(request.room_name, "room-1")
        self.assertEqual(request.sip_trunk_id, "ST_trunk")
        self.assertEqual(request.sip_call_to, "+821012345678")
        self.assertEqual(request.participant_identity, PHONE_PARTICIPANT_IDENTITY)
        self.assertTrue(request.wait_until_answered)

    async def test_unanswered_call_returns_false(self):
        """Test busy/declined/no-answer is an expected failure, not a crash"""
        sip = FakeSip(
            error=api.TwirpError(
                "unavailable",
                "busy",
                status=486,
                metadata={"sip_status_code": "486"},
            )
        )

        answered = await dial_phone(sip, "room-1", "ST_trunk", "+821012345678")

        self.assertFalse(answered)

    async def test_unanswered_call_does_not_log_phone_number(self):
        """Test the fan's phone number stays out of logs"""
        sip = FakeSip(error=api.TwirpError("unavailable", "busy", status=486))

        with self.assertLogs("fancall.agent.phone_dialer", level="WARNING") as logs:
            await dial_phone(sip, "room-1", "ST_trunk", "+821012345678")

        self.assertNotIn("+821012345678", "\n".join(logs.output))


if __name__ == "__main__":
    unittest.main()
