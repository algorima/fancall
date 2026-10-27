"""
Unit tests for sending each spoken line to the host app so it can store the call
"""

import asyncio
import json
import unittest
from typing import Any

from livekit.agents.llm import ChatMessage

from fancall.agent.transcript_stream import (
    TRANSCRIPT_TOPIC,
    publish_transcript_line,
    transcript_packet,
)


class _FakeParticipant:
    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def publish_data(self, payload: bytes, **kwargs: Any) -> None:
        self.sent.append({"payload": payload, **kwargs})


class _FakeRoom:
    def __init__(self) -> None:
        self.local_participant = _FakeParticipant()


class TranscriptPacketTest(unittest.TestCase):
    def test_fan_and_idol_lines_become_records(self):
        fan = ChatMessage(role="user", content=["Hi there"])
        idol = ChatMessage(role="assistant", content=["Hey you~"])
        self.assertEqual(
            json.loads(transcript_packet(fan) or b""),
            {"speaker": "fan", "text": "Hi there"},
        )
        self.assertEqual(
            json.loads(transcript_packet(idol) or b""),
            {"speaker": "idol", "text": "Hey you~"},
        )

    def test_korean_text_is_kept_as_is(self):
        packet = transcript_packet(ChatMessage(role="user", content=["안녕하세요"]))
        self.assertIn("안녕하세요", (packet or b"").decode("utf-8"))

    def test_system_and_empty_lines_are_skipped(self):
        self.assertIsNone(
            transcript_packet(ChatMessage(role="system", content=["rules"]))
        )
        self.assertIsNone(transcript_packet(ChatMessage(role="user", content=["  "])))

    def test_internal_prompts_are_skipped(self):
        for text in ("(The fan just picked up the video call.)",):
            self.assertIsNone(
                transcript_packet(ChatMessage(role="user", content=[text]))
            )

    def test_line_is_cut_to_the_memory_limit(self):
        packet = transcript_packet(ChatMessage(role="user", content=["가" * 900]))
        self.assertEqual(len(json.loads(packet or b"")["text"]), 500)


class PublishTranscriptLineTest(unittest.TestCase):
    def test_sends_reliably_on_the_transcript_topic(self):
        room = _FakeRoom()
        asyncio.run(
            publish_transcript_line(room, ChatMessage(role="user", content=["Hi"]))
        )
        sent = room.local_participant.sent
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0]["topic"], TRANSCRIPT_TOPIC)
        self.assertTrue(sent[0]["reliable"])

    def test_nothing_sent_for_skipped_lines(self):
        room = _FakeRoom()
        asyncio.run(
            publish_transcript_line(room, ChatMessage(role="system", content=["x"]))
        )
        self.assertEqual(room.local_participant.sent, [])

    def test_a_send_failure_does_not_break_the_call(self):
        room = _FakeRoom()

        async def boom(*_: Any, **__: Any) -> None:
            raise RuntimeError("down")

        room.local_participant.publish_data = boom  # type: ignore[method-assign]
        asyncio.run(
            publish_transcript_line(room, ChatMessage(role="user", content=["Hi"]))
        )


if __name__ == "__main__":
    unittest.main()
