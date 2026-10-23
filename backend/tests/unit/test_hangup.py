"""
Unit tests for ending the call as soon as the fan hangs up
"""

import unittest
from types import SimpleNamespace

from livekit import rtc

from fancall.agent.hangup import end_call_when_fan_leaves


class FakeRoom:
    """Room that lets the test fire participant events"""

    def __init__(self):
        self.handlers: dict[str, list] = {}

    def on(self, event: str, handler):
        self.handlers.setdefault(event, []).append(handler)

    def fire(self, event: str, participant):
        for handler in self.handlers.get(event, []):
            handler(participant)


class FakeJobContext:
    """Records what the hang-up handler asks the job to do"""

    def __init__(self):
        self.room = FakeRoom()
        self.calls: list[tuple] = []

    def delete_room(self):
        self.calls.append(("delete_room",))

    def shutdown(self, reason: str = ""):
        self.calls.append(("shutdown", reason))


def make_participant(kind) -> SimpleNamespace:
    return SimpleNamespace(identity="p", kind=kind)


FAN = rtc.ParticipantKind.PARTICIPANT_KIND_STANDARD
AGENT = rtc.ParticipantKind.PARTICIPANT_KIND_AGENT


class EndCallWhenFanLeavesTest(unittest.TestCase):
    def test_fan_leaving_deletes_room_and_ends_job(self):
        ctx = FakeJobContext()
        end_call_when_fan_leaves(ctx)  # type: ignore[arg-type]

        ctx.room.fire("participant_disconnected", make_participant(FAN))

        self.assertEqual(ctx.calls[0], ("delete_room",))
        self.assertEqual(ctx.calls[1][0], "shutdown")

    def test_avatar_leaving_does_not_end_the_call(self):
        ctx = FakeJobContext()
        end_call_when_fan_leaves(ctx)  # type: ignore[arg-type]

        # Simli 같은 아바타도 agent 참가자다. 아바타가 끊겨도 음성 통화는 이어진다
        ctx.room.fire("participant_disconnected", make_participant(AGENT))

        self.assertEqual(ctx.calls, [])

    def test_ends_only_once(self):
        ctx = FakeJobContext()
        end_call_when_fan_leaves(ctx)  # type: ignore[arg-type]

        ctx.room.fire("participant_disconnected", make_participant(FAN))
        ctx.room.fire("participant_disconnected", make_participant(FAN))

        self.assertEqual(len(ctx.calls), 2)


if __name__ == "__main__":
    unittest.main()
