"""
Unit tests for fancall Pydantic schemas
"""

import json
import unittest

from pydantic import ValidationError

from fancall.persona import Persona


class TestPersonaValidation(unittest.TestCase):
    """Tests for Persona model validation"""

    def test_parse_valid_json_with_all_fields(self):
        """Test parsing valid JSON with all fields"""
        metadata_json = json.dumps(
            {
                "avatar_id": "avatar_456",
                "profile_picture_url": "https://example.com/pic.jpg",
                "voice_id": "voice_789",
                "system_prompt": "You are helpful.",
            }
        )

        metadata = Persona.model_validate_json(metadata_json)

        self.assertEqual(metadata.avatar_id, "avatar_456")
        self.assertEqual(metadata.profile_picture_url, "https://example.com/pic.jpg")
        self.assertEqual(metadata.voice_id, "voice_789")
        self.assertEqual(metadata.system_prompt, "You are helpful.")

    def test_parse_empty_json(self):
        """Test that empty JSON (all optional fields) parses successfully"""
        metadata_json = json.dumps({})

        metadata = Persona.model_validate_json(metadata_json)

        self.assertIsNone(metadata.avatar_id)
        self.assertIsNone(metadata.profile_picture_url)
        self.assertIsNone(metadata.voice_id)
        self.assertIsNone(metadata.system_prompt)

    def test_parse_invalid_json(self):
        """Test that invalid JSON raises ValidationError"""
        invalid_json = "not valid json {"

        self.assertRaises(
            ValidationError, Persona.model_validate_json, invalid_json
        )

    def test_parse_with_extra_fields_ignored(self):
        """Test that extra fields are ignored due to extra='ignore' config"""
        metadata_json = json.dumps(
            {
                "avatar_id": "avatar_456",
                "unknown_field": "should_be_ignored",
                "another_extra": 123,
            }
        )

        metadata = Persona.model_validate_json(metadata_json)

        self.assertEqual(metadata.avatar_id, "avatar_456")
        # Extra fields should not be accessible
        self.assertFalse(hasattr(metadata, "unknown_field"))
        self.assertFalse(hasattr(metadata, "another_extra"))

    def test_field_defaults(self):
        """Test that optional fields default to None"""
        metadata = Persona.model_validate({})

        self.assertIsNone(metadata.avatar_id)
        self.assertIsNone(metadata.profile_picture_url)
        self.assertIsNone(metadata.voice_id)
        self.assertIsNone(metadata.system_prompt)

    def test_construct_with_all_fields(self):
        """Test constructing model instance with all fields"""
        metadata = Persona(
            avatar_id="avatar_456",
            profile_picture_url="https://example.com/pic.jpg",
            voice_id="voice_789",
            system_prompt="You are helpful.",
        )

        self.assertEqual(metadata.avatar_id, "avatar_456")
        self.assertEqual(metadata.profile_picture_url, "https://example.com/pic.jpg")
        self.assertEqual(metadata.voice_id, "voice_789")
        self.assertEqual(metadata.system_prompt, "You are helpful.")

    def test_empty_optional_strings_are_preserved(self):
        """Test that empty strings for optional fields are preserved (not converted to None)"""
        metadata = Persona.model_validate(
            {
                "avatar_id": "",
                "voice_id": "",
            }
        )

        self.assertEqual(metadata.avatar_id, "")
        self.assertEqual(metadata.voice_id, "")
