"""Unit tests for FIFOQueue edge cases, precision, and constraints."""

import unittest
from decimal import Decimal
from src.fifo_queue import FIFOQueue


class TestFIFOQueue(unittest.TestCase):

    def test_single_batch_add_and_consume(self):
        q = FIFOQueue()
        q.add(Decimal("100"), Decimal("50"))
        self.assertEqual(q.get_total_qty(), Decimal("100"))
        self.assertEqual(q.get_total_value(), Decimal("5000"))

        val, breakdown = q.consume(Decimal("40"))
        self.assertEqual(val, Decimal("2000"))
        self.assertEqual(q.get_total_qty(), Decimal("60"))
        self.assertEqual(q.get_total_value(), Decimal("3000"))

    def test_multi_batch_consumption(self):
        q = FIFOQueue()
        q.add(Decimal("20"), Decimal("50"))  # 1000
        q.add(Decimal("50"), Decimal("80"))  # 4000
        q.add(Decimal("50"), Decimal("60"))  # 3000
        self.assertEqual(q.get_total_qty(), Decimal("120"))
        self.assertEqual(q.get_total_value(), Decimal("8000"))

        # Consume 100 units across all 3 buckets
        val, breakdown = q.consume(Decimal("100"))
        # 20 @ 50 = 1000, 50 @ 80 = 4000, 30 @ 60 = 1800 -> Total: 6800
        self.assertEqual(val, Decimal("6800"))
        self.assertEqual(len(breakdown), 3)
        self.assertEqual(breakdown[0], (Decimal("20"), Decimal("50"), Decimal("1000")))
        self.assertEqual(breakdown[1], (Decimal("50"), Decimal("80"), Decimal("4000")))
        self.assertEqual(breakdown[2], (Decimal("30"), Decimal("60"), Decimal("1800")))

        # Remaining queue should have 20 @ 60 = 1200
        self.assertEqual(q.get_total_qty(), Decimal("20"))
        self.assertEqual(q.get_total_value(), Decimal("1200"))
        self.assertEqual(q.to_list(), [[Decimal("20"), Decimal("60")]])

    def test_merges_consecutive_identical_rates(self):
        q = FIFOQueue()
        q.add(Decimal("50"), Decimal("60"))
        q.add(Decimal("50"), Decimal("60"))
        # Should merge into one bucket of [100, 60]
        self.assertEqual(len(q.queue), 1)
        self.assertEqual(q.queue[0], [Decimal("100"), Decimal("60")])

    def test_negative_stock_exception(self):
        q = FIFOQueue()
        q.add(Decimal("10"), Decimal("50"))
        with self.assertRaises(ValueError) as ctx:
            q.consume(Decimal("15"))
        self.assertIn("Negative stock violation", str(ctx.exception))

    def test_clone_independence(self):
        q1 = FIFOQueue()
        q1.add(Decimal("50"), Decimal("10"))
        q2 = q1.clone()
        q2.consume(Decimal("20"))
        self.assertEqual(q1.get_total_qty(), Decimal("50"))
        self.assertEqual(q2.get_total_qty(), Decimal("30"))


if __name__ == "__main__":
    unittest.main()
