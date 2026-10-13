"""
Unit tests for the call timer that ends a video call with a goodbye
"""

import asyncio
import unittest

from fancall.agent.call_timer import run_call_timer
from fancall.prompts import CLOSING_INSTRUCTIONS, WRAP_UP_INSTRUCTIONS
from fancall.settings import FancallCallSettings


class FakeSpeechHandle:
    """Speech handle whose playout finishes after `playout` seconds"""

    def __init__(self, events: list, playout: float):
        self._events = events
        self._playout = playout

    async def wait_for_playout(self) -> None:
        await asyncio.sleep(self._playout)
        self._events.append(("playout_done",))


class FakeSession:
    """Records calls the timer makes on the agent session"""

    def __init__(self, events: list, playout: float = 0.0):
        self._events = events
        self._playout = playout

    def interrupt(self):
        self._events.append(("interrupt",))

    def generate_reply(self, *, instructions: str, allow_interruptions: bool):
        self._events.append(("generate_reply", instructions, allow_interruptions))
        return FakeSpeechHandle(self._events, self._playout)


class FakeAgent:
    """Records instruction updates"""

    def __init__(self, events: list):
        self._events = events

    async def update_instructions(self, instructions: str) -> None:
        self._events.append(("update_instructions", instructions))


class FakeClock:
    """Sleep replacement that records waits instead of waiting"""

    def __init__(self, events: list):
        self._events = events

    async def sleep(self, seconds: float) -> None:
        self._events.append(("sleep", seconds))


def make_settings(**overrides) -> FancallCallSettings:
    values = {
        "call_duration_seconds": 180,
        "wrap_up_lead_seconds": 30,
        "closing_lead_seconds": 12,
        "closing_grace_seconds": 5,
    }
    values.update(overrides)
    return FancallCallSettings.model_validate(values)


class TestRunCallTimer(unittest.IsolatedAsyncioTestCase):
    """Tests for run_call_timer"""

    async def test_wraps_up_then_says_goodbye_on_schedule(self):
        """Test wrap-up hint at T-30s and a non-interruptible goodbye at T-12s"""
        events: list = []

        await run_call_timer(
            FakeSession(events),
            FakeAgent(events),
            "base",
            make_settings(),
            sleep=FakeClock(events).sleep,
        )

        self.assertEqual(events[0], ("sleep", 150))
        self.assertEqual(
            events[1],
            (
                "update_instructions",
                "base\n\n" + WRAP_UP_INSTRUCTIONS.format(lead_seconds=30),
            ),
        )
        self.assertIn("30초쯤 남았다", events[1][1])
        self.assertEqual(events[2], ("sleep", 18))
        self.assertEqual(events[3], ("interrupt",))
        self.assertEqual(events[4], ("generate_reply", CLOSING_INSTRUCTIONS, False))
        self.assertEqual(events[5], ("playout_done",))

    async def test_returns_after_grace_when_goodbye_runs_long(self):
        """Test the timer stops waiting once closing lead plus grace has passed"""
        events: list = []
        settings = make_settings(
            call_duration_seconds=1,
            wrap_up_lead_seconds=0.5,
            closing_lead_seconds=0.02,
            closing_grace_seconds=0.02,
        )

        await asyncio.wait_for(
            run_call_timer(
                FakeSession(events, playout=10),
                FakeAgent(events),
                "base",
                settings,
                sleep=FakeClock(events).sleep,
            ),
            timeout=1,
        )

        self.assertNotIn(("playout_done",), events)

    async def test_wrap_up_follows_lead_setting(self):
        """Test the wrap-up hint states the configured lead, not a fixed 30s"""
        events: list = []

        await run_call_timer(
            FakeSession(events),
            FakeAgent(events),
            "base",
            make_settings(wrap_up_lead_seconds=45),
            sleep=FakeClock(events).sleep,
        )

        self.assertIn("45초쯤 남았다", events[1][1])
        self.assertNotIn("30초", events[1][1])


class TestFancallCallSettings(unittest.TestCase):
    """Tests for call timing validation"""

    def test_default_call_is_three_minutes(self):
        """Test default call length"""
        self.assertEqual(FancallCallSettings().call_duration_seconds, 180)

    def test_rejects_leads_out_of_order(self):
        """Test closing must come after wrap-up and both inside the call"""
        with self.assertRaises(ValueError):
            make_settings(wrap_up_lead_seconds=10, closing_lead_seconds=12)
        with self.assertRaises(ValueError):
            make_settings(call_duration_seconds=20, wrap_up_lead_seconds=30)


if __name__ == "__main__":
    unittest.main()
