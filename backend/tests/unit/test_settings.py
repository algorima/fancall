"""
Unit tests for fancall settings
"""

import os
import unittest
from unittest.mock import patch

from fancall.settings import CorsSettings


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


if __name__ == "__main__":
    unittest.main()
