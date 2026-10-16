"""
Unit tests for waiting until the fan answers the call
"""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock

from fancall.agent.worker import wait_for_answer


class TestWaitForAnswer(unittest.IsolatedAsyncioTestCase):
    """Test cases for wait_for_answer"""

    async def test_returns_true_when_fan_joins(self) -> None:
        """The call proceeds once the fan joins the room"""
        ctx = MagicMock()
        ctx.wait_for_participant = AsyncMock()

        answered = await wait_for_answer(ctx, timeout=1)

        self.assertTrue(answered)
        ctx.shutdown.assert_not_called()

    async def test_shuts_down_when_unanswered(self) -> None:
        """An unanswered call ends the job without greeting or starting the timer"""

        async def never_joins() -> None:
            await asyncio.Event().wait()

        ctx = MagicMock()
        ctx.wait_for_participant = never_joins

        answered = await wait_for_answer(ctx, timeout=0.01)

        self.assertFalse(answered)
        ctx.shutdown.assert_called_once()


if __name__ == "__main__":
    unittest.main()
