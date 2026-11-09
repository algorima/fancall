"""
Unit tests for fancall Pydantic schemas
"""

import json
import unittest

from pydantic import ValidationError

from fancall.schemas import AgentDispatchRequest


class TestAgentDispatchRequestValidation(unittest.TestCase):
    """Tests for AgentDispatchRequest model validation"""

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

        metadata = AgentDispatchRequest.model_validate_json(metadata_json)

        self.assertEqual(metadata.avatar_id, "avatar_456")
        self.assertEqual(metadata.profile_picture_url, "https://example.com/pic.jpg")
        self.assertEqual(metadata.voice_id, "voice_789")
        self.assertEqual(metadata.system_prompt, "You are helpful.")

    def test_parse_empty_json(self):
        """Test that empty JSON (all optional fields) parses successfully"""
        metadata_json = json.dumps({})

        metadata = AgentDispatchRequest.model_validate_json(metadata_json)

        self.assertIsNone(metadata.avatar_id)
        self.assertIsNone(metadata.profile_picture_url)
        self.assertIsNone(metadata.voice_id)
        self.assertIsNone(metadata.system_prompt)

    def test_parse_invalid_json(self):
        """Test that invalid JSON raises ValidationError"""
        invalid_json = "not valid json {"

        self.assertRaises(
            ValidationError, AgentDispatchRequest.model_validate_json, invalid_json
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

        metadata = AgentDispatchRequest.model_validate_json(metadata_json)

        self.assertEqual(metadata.avatar_id, "avatar_456")
        # Extra fields should not be accessible
        self.assertFalse(hasattr(metadata, "unknown_field"))
        self.assertFalse(hasattr(metadata, "another_extra"))

    def test_field_defaults(self):
        """Test that optional fields default to None"""
        metadata = AgentDispatchRequest.model_validate({})

        self.assertIsNone(metadata.avatar_id)
        self.assertIsNone(metadata.profile_picture_url)
        self.assertIsNone(metadata.voice_id)
        self.assertIsNone(metadata.system_prompt)

    def test_construct_with_all_fields(self):
        """Test constructing model instance with all fields"""
        metadata = AgentDispatchRequest(
            avatar_id="avatar_456",
            profile_picture_url="https://example.com/pic.jpg",
            voice_id="voice_789",
            system_prompt="You are helpful.",
        )

        self.assertEqual(metadata.avatar_id, "avatar_456")
        self.assertEqual(metadata.profile_picture_url, "https://example.com/pic.jpg")
        self.assertEqual(metadata.voice_id, "voice_789")
        self.assertEqual(metadata.system_prompt, "You are helpful.")

    def test_phone_call_defaults_to_video_call(self):
        """Test existing dispatches without phone_call stay video calls"""
        metadata = AgentDispatchRequest.model_validate({})

        self.assertFalse(metadata.phone_call)

    def test_phone_call_round_trips_through_job_metadata(self):
        """Test phone_call survives the dispatch metadata JSON the worker parses"""
        metadata_json = AgentDispatchRequest(phone_call=True).model_dump_json(
            exclude_none=True
        )

        metadata = AgentDispatchRequest.model_validate_json(metadata_json)

        self.assertTrue(metadata.phone_call)

    def test_opening_message_round_trips_through_job_metadata(self):
        """Test the fixed opening line reaches the worker unchanged"""
        metadata_json = AgentDispatchRequest(
            opening_message="안녕, 소연이 맞지! 난 시연이야."
        ).model_dump_json(exclude_none=True)

        metadata = AgentDispatchRequest.model_validate_json(metadata_json)

        self.assertEqual(metadata.opening_message, "안녕, 소연이 맞지! 난 시연이야.")

    def test_phone_number_accepts_e164(self):
        """Test an E.164 phone number is accepted"""
        metadata = AgentDispatchRequest(phone_number="+821012345678")

        self.assertEqual(metadata.phone_number, "+821012345678")

    def test_phone_number_rejects_non_e164(self):
        """Test local formats are rejected so SIP never dials a wrong number"""
        for phone_number in ("010-1234-5678", "01012345678", "+0123456789", ""):
            with self.subTest(phone_number=phone_number):
                self.assertRaises(
                    ValidationError,
                    AgentDispatchRequest,
                    phone_number=phone_number,
                )

    def test_empty_optional_strings_are_preserved(self):
        """Test that empty strings for optional fields are preserved (not converted to None)"""
        metadata = AgentDispatchRequest.model_validate(
            {
                "avatar_id": "",
                "voice_id": "",
            }
        )

        self.assertEqual(metadata.avatar_id, "")
        self.assertEqual(metadata.voice_id, "")
