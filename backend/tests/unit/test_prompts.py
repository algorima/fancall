"""
Unit tests for fancall prompt composition
"""

import unittest

from fancall.prompts import (
    CLOSING_INSTRUCTIONS,
    OPENING_INSTRUCTIONS,
    ROLE_PLAYING_GUIDELINES,
    VIDEO_CALL_GUIDELINES,
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


class TestVideoCallGuidelines(unittest.TestCase):
    """Tests for the content contract of video call prompts"""

    def test_guidelines_forbid_spoken_action_markup(self):
        """Test guidelines tell the model not to write text that TTS reads aloud"""
        self.assertIn("별표", VIDEO_CALL_GUIDELINES)
        self.assertIn("괄호", VIDEO_CALL_GUIDELINES)

    def test_guidelines_forbid_pretending_to_see_fan(self):
        """Test guidelines block inventing what the fan's camera shows"""
        self.assertIn("보인다고 지어내지", VIDEO_CALL_GUIDELINES)

    def test_opening_and_closing_are_not_empty(self):
        """Test call opening and closing instructions exist"""
        self.assertTrue(OPENING_INSTRUCTIONS.strip())
        self.assertTrue(CLOSING_INSTRUCTIONS.strip())


if __name__ == "__main__":
    unittest.main()
