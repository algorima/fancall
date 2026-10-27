"""
Unit tests for the stored lines of earlier calls (per signed-in fan and trainee)
"""

import unittest

from aioia_core.models import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from fancall.repositories.call_memory_repository import (
    MAX_STORED_LINES,
    CallMemoryRepository,
)
from fancall.schemas import MemoryLine


def _line(speaker: str, text: str) -> MemoryLine:
    return MemoryLine(speaker=speaker, text=text)  # type: ignore[arg-type]


class CallMemoryRepositoryTest(unittest.TestCase):
    def setUp(self) -> None:
        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        self.session = Session(engine)
        self.repository = CallMemoryRepository(self.session)

    def tearDown(self) -> None:
        self.session.close()

    def test_returns_lines_oldest_first(self):
        self.repository.append(
            "u1", "t1", [_line("fan", "first"), _line("idol", "second")]
        )
        self.repository.append("u1", "t1", [_line("fan", "third")])
        recent = self.repository.recent("u1", "t1")
        self.assertEqual([line.text for line in recent], ["first", "second", "third"])
        self.assertEqual(recent[1].speaker, "idol")

    def test_keeps_each_fan_and_trainee_apart(self):
        self.repository.append("u1", "t1", [_line("fan", "mine")])
        self.repository.append("u2", "t1", [_line("fan", "other fan")])
        self.repository.append("u1", "t2", [_line("fan", "other trainee")])
        self.assertEqual(
            [line.text for line in self.repository.recent("u1", "t1")], ["mine"]
        )

    def test_unknown_fan_has_no_memory(self):
        self.assertEqual(self.repository.recent("nobody", "t1"), [])

    def test_keeps_only_the_latest_lines(self):
        lines = [_line("fan", f"line {i}") for i in range(MAX_STORED_LINES + 5)]
        for start in range(0, len(lines), 50):
            self.repository.append("u1", "t1", lines[start : start + 50])
        recent = self.repository.recent("u1", "t1")
        self.assertEqual(len(recent), MAX_STORED_LINES)
        self.assertEqual(recent[-1].text, f"line {MAX_STORED_LINES + 4}")
        self.assertEqual(recent[0].text, "line 5")

    def test_recent_honors_a_smaller_limit(self):
        self.repository.append("u1", "t1", [_line("fan", str(i)) for i in range(10)])
        self.assertEqual(
            [line.text for line in self.repository.recent("u1", "t1", limit=3)],
            ["7", "8", "9"],
        )

    def test_delete_removes_only_that_fans_memory_of_that_trainee(self):
        self.repository.append("u1", "t1", [_line("fan", "a")])
        self.repository.append("u1", "t2", [_line("fan", "b")])
        self.repository.append("u2", "t1", [_line("fan", "c")])
        self.assertEqual(self.repository.delete("u1", "t1"), 1)
        self.assertEqual(self.repository.recent("u1", "t1"), [])
        self.assertEqual(len(self.repository.recent("u1", "t2")), 1)
        self.assertEqual(len(self.repository.recent("u2", "t1")), 1)

    def test_appended_order_survives_lines_stored_in_one_call(self):
        self.repository.append(
            "u1", "t1", [_line("idol", "x"), _line("fan", "y"), _line("idol", "z")]
        )
        self.assertEqual(
            [line.text for line in self.repository.recent("u1", "t1")], ["x", "y", "z"]
        )


if __name__ == "__main__":
    unittest.main()
