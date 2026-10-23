"""
Unit tests for prepared replies to set-phrase fan lines
"""

import random
import unittest

from fancall.agent.fast_reply import LINES, FanMove, FastReplies, fan_move


class FanMoveTest(unittest.TestCase):
    def test_set_phrase_lines(self):
        self.assertEqual(fan_move("오늘 너무 잘생겼어요"), FanMove.LOOKS)
        self.assertEqual(fan_move("You're so cute"), FanMove.LOOKS)
        self.assertEqual(fan_move("사랑해 ~ ~ 빠빠"), FanMove.GOODBYE)
        self.assertEqual(fan_move("항상 응원해요"), FanMove.LOVE)
        self.assertEqual(fan_move("저 팬싸 처음이에요!"), FanMove.FIRST_TIME)
        self.assertEqual(fan_move("Hi!"), FanMove.GREETING)

    def test_questions_go_to_the_llm(self):
        self.assertIsNone(fan_move("Hi. Nice to meet you. What's your name?"))
        self.assertIsNone(fan_move("오늘 왜 이렇게 잘생겼어?"))
        self.assertIsNone(fan_move("나 기억나?"))

    def test_misheard_name_is_not_a_goodbye(self):
        # "Seojun, hi" was transcribed as "See you, Jen. Hi" (2026-10-23)
        self.assertIsNone(fan_move("Yes. I can hear you perfectly. See you, Jen. Hi."))

    def test_lines_matching_two_kinds_go_to_the_llm(self):
        self.assertIsNone(fan_move("You're so cute, I love you"))

    def test_other_lines_go_to_the_llm(self):
        self.assertIsNone(fan_move("I had an exam today."))
        self.assertIsNone(fan_move(""))
        long_line = "오빠 저 오늘 시험 봤는데 진짜 망해서 기분이 너무 안 좋았는데 오빠 보니까 좋아요"
        self.assertIsNone(fan_move(long_line))


class FastRepliesTest(unittest.TestCase):
    def test_replies_in_the_fans_language(self):
        ko = FastReplies("ko").pick("너무 귀여워")
        self.assertIn(ko, [line.ko for line in LINES[FanMove.LOOKS]])
        en = FastReplies("en").pick("Bye!")
        self.assertIn(en, [line.en for line in LINES[FanMove.GOODBYE]])

    def test_none_when_the_llm_should_answer(self):
        self.assertIsNone(FastReplies("en").pick("What did you practice today?"))

    def test_does_not_repeat_the_same_line_twice_in_a_row(self):
        replies = FastReplies("ko", rng=random.Random(0))
        picked = [replies.pick("너무 귀여워") for _ in range(30)]
        for prev, cur in zip(picked, picked[1:]):
            self.assertNotEqual(prev, cur)

    def test_lists_every_line_for_prerendering(self):
        self.assertEqual(
            len(FastReplies("ja").lines), sum(len(v) for v in LINES.values())
        )


if __name__ == "__main__":
    unittest.main()
