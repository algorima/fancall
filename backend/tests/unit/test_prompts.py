"""
Unit tests for fancall prompt composition
"""

import unittest

from fancall.prompts import (
    CLOSING_INSTRUCTIONS,
    OPENING_INSTRUCTIONS,
    PHONE_CALL_GUIDELINES,
    PHONE_OPENING_MESSAGE,
    ROLE_PLAYING_GUIDELINES,
    VIDEO_CALL_GUIDELINES,
    WRAP_UP_INSTRUCTIONS,
    compose_instructions,
)


class TestComposeInstructions(unittest.TestCase):
    """Tests for compose_instructions"""

    def test_default_keeps_role_playing_guidelines(self):
        """Test default call still includes role playing guidelines only"""
        result = compose_instructions("persona")

        self.assertIn(ROLE_PLAYING_GUIDELINES, result)
        self.assertNotIn(VIDEO_CALL_GUIDELINES, result)
        self.assertTrue(result.endswith("persona"))

    def test_video_call_replaces_role_playing_guidelines(self):
        """Test video call mode uses call guidelines without *action* roleplay"""
        result = compose_instructions(
            "persona", include_role_playing=False, include_video_call=True
        )

        self.assertIn(VIDEO_CALL_GUIDELINES, result)
        self.assertNotIn(ROLE_PLAYING_GUIDELINES, result)

    def test_persona_comes_after_video_call_guidelines(self):
        """Test persona prompt follows call guidelines so persona tone applies"""
        result = compose_instructions(
            "persona", include_role_playing=False, include_video_call=True
        )

        self.assertLess(result.index(VIDEO_CALL_GUIDELINES), result.index("persona"))

    def test_video_call_without_persona(self):
        """Test video call guidelines alone when no system prompt is given"""
        result = compose_instructions(
            None, include_role_playing=False, include_video_call=True
        )

        self.assertEqual(result, VIDEO_CALL_GUIDELINES)

    def test_video_call_excludes_phone_call_guidelines(self):
        """Test video call mode does not tell the model it is on a phone"""
        result = compose_instructions(
            "persona", include_role_playing=False, include_video_call=True
        )

        self.assertNotIn(PHONE_CALL_GUIDELINES, result)

    def test_phone_call_builds_on_video_call_guidelines(self):
        """Test phone call keeps the fan call rhythm and adds phone rules after it"""
        result = compose_instructions(
            "persona", include_role_playing=False, include_phone_call=True
        )

        self.assertIn(VIDEO_CALL_GUIDELINES, result)
        self.assertLess(
            result.index(VIDEO_CALL_GUIDELINES), result.index(PHONE_CALL_GUIDELINES)
        )
        self.assertLess(result.index(PHONE_CALL_GUIDELINES), result.index("persona"))


class TestPhoneCallGuidelines(unittest.TestCase):
    """Tests for the content contract of phone call prompts"""

    def test_phone_guidelines_say_fan_cannot_see_idol(self):
        """Test phone guidelines override the video call face/screen rules"""
        self.assertIn("볼 수 없다", PHONE_CALL_GUIDELINES)

    def test_phone_opening_starts_like_a_phone_call(self):
        """Test the fixed phone opening greets like a phone call, not a video check"""
        self.assertIn("여보세요", PHONE_OPENING_MESSAGE)
        self.assertNotIn("화면", PHONE_OPENING_MESSAGE)

    def test_phone_guidelines_forbid_claiming_to_be_human(self):
        """Test the model admits it is AI when asked"""
        self.assertIn("사람이라고 말하지 않는다", PHONE_CALL_GUIDELINES)

    def test_phone_guidelines_forbid_sales(self):
        """Test phone calls carry no sales or promotion"""
        self.assertIn("판매나 홍보를 하지 않는다", PHONE_CALL_GUIDELINES)

    def test_phone_guidelines_give_crisis_lines(self):
        """Test crisis talk gets the Korean and US hotlines"""
        self.assertIn("109", PHONE_CALL_GUIDELINES)
        self.assertIn("988", PHONE_CALL_GUIDELINES)


class TestVideoCallGuidelines(unittest.TestCase):
    """Tests for the content contract of video call prompts"""

    def test_guidelines_forbid_spoken_action_markup(self):
        """Test guidelines tell the model not to write text that TTS reads aloud"""
        self.assertIn("별표", VIDEO_CALL_GUIDELINES)
        self.assertIn("괄호", VIDEO_CALL_GUIDELINES)

    def test_guidelines_forbid_pretending_to_see_fan(self):
        """Test guidelines block inventing what the fan's camera shows"""
        self.assertIn("보인다고 지어내지", VIDEO_CALL_GUIDELINES)

    def test_opening_does_not_claim_to_see_fan(self):
        """Test opening example does not say the fan's screen is visible"""
        self.assertNotIn("보여요 보여요", OPENING_INSTRUCTIONS)

    def test_opening_and_closing_are_not_empty(self):
        """Test call opening and closing instructions exist"""
        self.assertTrue(OPENING_INSTRUCTIONS.strip())
        self.assertTrue(WRAP_UP_INSTRUCTIONS.strip())
        self.assertTrue(CLOSING_INSTRUCTIONS.strip())

    def test_closing_forbids_new_questions(self):
        """Test goodbye instructions keep the model from opening a new topic"""
        self.assertIn("질문은 절대 하지 않는다", CLOSING_INSTRUCTIONS)


if __name__ == "__main__":
    unittest.main()
