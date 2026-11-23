import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from services.system.log import get_log_page


class LogLatencyTests(unittest.IsolatedAsyncioTestCase):
    async def test_page_returns_recorded_latency(self) -> None:
        """分页保留实际耗时，零值和缺值不被替换。"""
        for latency in (0, 37, None):
            with self.subTest(latency=latency):
                count_result = MagicMock()
                count_result.scalar.return_value = 1
                page_result = MagicMock()
                page_result.scalars.return_value.all.return_value = [
                    SimpleNamespace(
                        id=1,
                        username="tester",
                        method="GET",
                        url="/example",
                        status="success",
                        error=None,
                        type=1,
                        latency=latency,
                        create_at=datetime(2026, 1, 1),
                    )
                ]
                db = AsyncMock()
                db.execute.side_effect = [count_result, page_result]
                result = await get_log_page(db)
                self.assertEqual(result["items"][0]["latency"], latency)
                self.assertNotIn("ip", result["items"][0])


if __name__ == "__main__":
    unittest.main()
