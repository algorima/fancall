"""
Unit tests for fancall settings
"""

import os
import unittest
from unittest.mock import patch

from pydantic import ValidationError

from fancall.settings import CorsSettings, FancallModelSettings


class TestCorsSettings(unittest.TestCase):
    """Test cases for CorsSettings"""

    def test_defaults_to_local_dev_origin(self) -> None:
        """Without configuration only the local dev frontend is allowed"""
        with patch.dict(os.environ, clear=True):
            self.assertEqual(CorsSettings().origins, ["http://localhost:3000"])

    def test_parses_comma_separated_origins(self) -> None:
        """Origins come from the environment, trimmed, without blanks"""
        env = {"CORS_ALLOWED_ORIGINS": "https://a.com, https://b.com,,"}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(CorsSettings().origins, ["https://a.com", "https://b.com"])


class TestFancallModelSettings(unittest.TestCase):
    """Test cases for FancallModelSettings"""

    def test_reasoning_effort_unset_by_default(self) -> None:
        """Without configuration the plugin default reasoning effort is kept"""
        with patch.dict(os.environ, clear=True):
            self.assertIsNone(FancallModelSettings().openai_reasoning_effort)

    def test_reads_reasoning_effort(self) -> None:
        """FANCALL_OPENAI_REASONING_EFFORT sets the effort sent to the LLM"""
        env = {"FANCALL_OPENAI_REASONING_EFFORT": "low"}
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(FancallModelSettings().openai_reasoning_effort, "low")

    def test_rejects_unknown_reasoning_effort(self) -> None:
        """A typo fails at startup instead of on the first call"""
        env = {"FANCALL_OPENAI_REASONING_EFFORT": "fast"}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ValidationError):
                FancallModelSettings()


if __name__ == "__main__":
    unittest.main()
