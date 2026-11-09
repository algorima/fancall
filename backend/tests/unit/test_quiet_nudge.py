"""
Unit tests for the nudge that keeps a video call from going quiet
"""

import asyncio
import unittest

from fancall.agent.quiet_nudge import QuietNudger
from fancall.prompts import QUIET_NUDGE_INSTRUCTIONS, QUIET_NUDGE_USER_INPUT

QUIET = 0.01


class FakeSession:
    """Records the replies the nudger asks for"""

    def __init__(self):
        self.replies: list[tuple[str, str]] = []

    def generate_reply(self, *, user_input: str, instructions: str):
        self.replies.append((user_input, instructions))


def make_nudger(session: FakeSession, max_in_row: int = 2) -> QuietNudger:
    return QuietNudger(session, quiet_seconds=QUIET, max_in_row=max_in_row)


class QuietNudgerTest(unittest.IsolatedAsyncioTestCase):
    async def test_speaks_first_when_fan_stays_quiet(self):
        session = FakeSession()
        nudger = make_nudger(session)

        nudger.on_agent_state("listening")
        await asyncio.sleep(QUIET * 5)

        self.assertEqual(
            session.replies, [(QUIET_NUDGE_USER_INPUT, QUIET_NUDGE_INSTRUCTIONS)]
        )

    async def test_fan_message_cancels_the_nudge(self):
        session = FakeSession()
        nudger = make_nudger(session)

        nudger.on_agent_state("listening")
        nudger.on_user_message("Hi!")
        await asyncio.sleep(QUIET * 5)

        self.assertEqual(session.replies, [])

    async def test_no_nudge_while_agent_is_speaking(self):
        session = FakeSession()
        nudger = make_nudger(session)

        nudger.on_agent_state("listening")
        nudger.on_agent_state("speaking")
        await asyncio.sleep(QUIET * 5)

        self.assertEqual(session.replies, [])

    async def test_stops_after_max_nudges_in_a_row(self):
        session = FakeSession()
        nudger = make_nudger(session, max_in_row=2)

        for _ in range(3):
            nudger.on_agent_state("listening")
            await asyncio.sleep(QUIET * 5)
            # 한마디를 하는 동안은 말하는 상태다
            nudger.on_agent_state("speaking")
            # 자기 한마디용 팬 쪽 지문은 팬 메시지로 치지 않는다
            nudger.on_user_message(QUIET_NUDGE_USER_INPUT)

        self.assertEqual(len(session.replies), 2)

    async def test_fan_reply_resets_the_limit(self):
        session = FakeSession()
        nudger = make_nudger(session, max_in_row=1)

        nudger.on_agent_state("listening")
        await asyncio.sleep(QUIET * 5)
        nudger.on_user_message("Sorry, I was typing")
        nudger.on_agent_state("listening")
        await asyncio.sleep(QUIET * 5)

        self.assertEqual(len(session.replies), 2)

    async def test_stop_cancels_pending_and_future_nudges(self):
        session = FakeSession()
        nudger = make_nudger(session)

        nudger.on_agent_state("listening")
        nudger.stop()
        nudger.on_agent_state("listening")
        await asyncio.sleep(QUIET * 5)

        self.assertEqual(session.replies, [])

    async def test_waits_while_fan_is_speaking(self):
        session = FakeSession()
        nudger = make_nudger(session)

        nudger.on_agent_state("listening")
        nudger.on_user_state("speaking")
        await asyncio.sleep(QUIET * 5)

        self.assertEqual(session.replies, [])

    async def test_counts_again_after_fan_stops_speaking(self):
        session = FakeSession()
        nudger = make_nudger(session)

        nudger.on_agent_state("listening")
        nudger.on_user_state("speaking")
        nudger.on_user_state("listening")
        await asyncio.sleep(QUIET * 5)

        self.assertEqual(len(session.replies), 1)

    async def test_zero_max_disables_nudges(self):
        session = FakeSession()
        nudger = make_nudger(session, max_in_row=0)

        nudger.on_agent_state("listening")
        await asyncio.sleep(QUIET * 5)

        self.assertEqual(session.replies, [])


if __name__ == "__main__":
    unittest.main()
