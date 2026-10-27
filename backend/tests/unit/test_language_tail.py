"""
Unit tests for the language reminder added to the fan's last message
"""

import unittest

from livekit.agents.llm import ChatContext, ChatMessage

from fancall.agent.language_tail import language_tail, with_language_tail


def _texts(ctx: ChatContext) -> list[str]:
    return [
        item.text_content or "" for item in ctx.items if isinstance(item, ChatMessage)
    ]


class LanguageTailTest(unittest.TestCase):
    def test_no_reminder_for_korean_or_unknown(self):
        self.assertEqual(language_tail("ko"), "")
        self.assertEqual(language_tail("ko-KR"), "")
        self.assertEqual(language_tail(None), "")
        self.assertEqual(language_tail(""), "")

    def test_reminder_names_the_language_and_forbids_hangul(self):
        tail = language_tail("en")
        self.assertIn("English", tail)
        self.assertIn("Korean", tail)
        self.assertIn("Japanese", language_tail("ja-JP"))

    def test_unknown_language_code_is_still_named(self):
        self.assertIn("th", language_tail("th"))


class WithLanguageTailTest(unittest.TestCase):
    def _ctx(self) -> ChatContext:
        ctx = ChatContext()
        ctx.add_message(role="user", content="first")
        ctx.add_message(role="assistant", content="reply")
        ctx.add_message(role="user", content="Hi! Can you hear me?")
        return ctx

    def test_appends_to_the_last_user_message_only(self):
        ctx = with_language_tail(self._ctx(), "(English only)")
        texts = _texts(ctx)
        self.assertEqual(texts[0], "first")
        self.assertEqual(texts[1], "reply")
        self.assertIn("Hi! Can you hear me?", texts[2])
        self.assertIn("(English only)", texts[2])

    def test_leaves_the_original_conversation_alone(self):
        original = self._ctx()
        with_language_tail(original, "(English only)")
        self.assertEqual(_texts(original)[-1], "Hi! Can you hear me?")

    def test_empty_tail_returns_the_same_context(self):
        original = self._ctx()
        self.assertIs(with_language_tail(original, ""), original)

    def test_no_user_message_returns_a_copy_unchanged(self):
        ctx = ChatContext()
        ctx.add_message(role="assistant", content="hello")
        out = with_language_tail(ctx, "(English only)")
        self.assertEqual(_texts(out)[-1], "hello")


if __name__ == "__main__":
    unittest.main()
