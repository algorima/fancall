"""
Unit tests for ending the call as soon as the fan hangs up
"""

import asyncio
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
        self.deleting: asyncio.Future[None] | None = None

    def delete_room(self) -> asyncio.Future[None]:
        self.calls.append(("delete_room",))
        self.deleting = asyncio.get_running_loop().create_future()
        return self.deleting

    def shutdown(self, reason: str = ""):
        self.calls.append(("shutdown", reason))


def make_participant(kind) -> SimpleNamespace:
    return SimpleNamespace(identity="p", kind=kind)


FAN = rtc.ParticipantKind.PARTICIPANT_KIND_STANDARD
AGENT = rtc.ParticipantKind.PARTICIPANT_KIND_AGENT


class EndCallWhenFanLeavesTest(unittest.IsolatedAsyncioTestCase):
    async def test_fan_leaving_deletes_room_and_ends_job(self):
        ctx = FakeJobContext()
        end_call_when_fan_leaves(ctx)  # type: ignore[arg-type]

        ctx.room.fire("participant_disconnected", make_participant(FAN))
        assert ctx.deleting is not None
        ctx.deleting.set_result(None)
        await asyncio.sleep(0)

        self.assertEqual(ctx.calls[0], ("delete_room",))
        self.assertEqual(ctx.calls[1][0], "shutdown")

    async def test_shutdown_waits_until_room_is_deleted(self):
        """shutdown 이 삭제 요청을 끊지 않도록 삭제가 끝난 뒤에 부른다"""
        ctx = FakeJobContext()
        end_call_when_fan_leaves(ctx)  # type: ignore[arg-type]

        ctx.room.fire("participant_disconnected", make_participant(FAN))
        await asyncio.sleep(0)

        self.assertEqual(ctx.calls, [("delete_room",)])

    async def test_avatar_leaving_does_not_end_the_call(self):
        ctx = FakeJobContext()
        end_call_when_fan_leaves(ctx)  # type: ignore[arg-type]

        # Simli 같은 아바타도 agent 참가자다. 아바타가 끊겨도 음성 통화는 이어진다
        ctx.room.fire("participant_disconnected", make_participant(AGENT))

        self.assertEqual(ctx.calls, [])

    async def test_ends_only_once(self):
        ctx = FakeJobContext()
        end_call_when_fan_leaves(ctx)  # type: ignore[arg-type]

        ctx.room.fire("participant_disconnected", make_participant(FAN))
        ctx.room.fire("participant_disconnected", make_participant(FAN))
        assert ctx.deleting is not None
        ctx.deleting.set_result(None)
        await asyncio.sleep(0)

        self.assertEqual(len(ctx.calls), 2)


if __name__ == "__main__":
    unittest.main()
