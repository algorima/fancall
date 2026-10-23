"""
Unit tests for how the companion agent opens a call
"""

import unittest
from unittest.mock import MagicMock, PropertyMock, patch

from fancall.agent.worker import CompanionAgent
from fancall.prompts import OPENING_INSTRUCTIONS, PHONE_OPENING_INSTRUCTIONS


class TestCompanionAgentOnEnter(unittest.IsolatedAsyncioTestCase):
    """Tests for the first line the agent speaks when the call connects"""

    async def _enter(self, agent: CompanionAgent) -> MagicMock:
        session = MagicMock()
        with patch.object(
            CompanionAgent, "session", new_callable=PropertyMock, return_value=session
        ):
            await agent.on_enter()
        return session

    async def test_video_call_generates_video_opening_by_default(self):
        """Test the video call opening is generated from the video instructions"""
        session = await self._enter(CompanionAgent(instructions="persona"))

        session.generate_reply.assert_called_once_with(
            instructions=OPENING_INSTRUCTIONS
        )
        session.say.assert_not_called()

    async def test_phone_call_generates_phone_opening(self):
        """Test the phone opening is generated in character, not read verbatim"""
        session = await self._enter(
            CompanionAgent(
                instructions="persona",
                opening_instructions=PHONE_OPENING_INSTRUCTIONS,
            )
        )

        session.generate_reply.assert_called_once_with(
            instructions=PHONE_OPENING_INSTRUCTIONS
        )
        session.say.assert_not_called()

    async def test_host_opening_message_is_read_verbatim_and_interruptible(self):
        """Test a host-provided opening is spoken as is and the fan can cut in"""
        session = await self._enter(
            CompanionAgent(
                instructions="persona",
                opening_instructions=PHONE_OPENING_INSTRUCTIONS,
                opening_message="여보세요? 지민이니?",
            )
        )

        session.say.assert_called_once_with("여보세요? 지민이니?")
        session.generate_reply.assert_not_called()


if __name__ == "__main__":
    unittest.main()
