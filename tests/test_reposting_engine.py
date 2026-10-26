"""Unit tests for RepostEngine idempotency, rate reduction, and DAG tracking."""

import unittest
from decimal import Decimal
from src.models import Item, StockTransaction, VoucherType
from src.ledger import StockLedger
from src.repost_engine import RepostEngine
from src.demo import build_scenario_ledger


class TestRepostingEngine(unittest.TestCase):

    def test_reposting_idempotency(self):
        """Running recalculation multiple times with same data must yield identical results."""
        ledger, _, _ = build_scenario_ledger()
        engine = RepostEngine(ledger)

        res1 = engine.simulate_rate_edit("PR-001", "Milk", Decimal("75.00"))
        res2 = engine.simulate_rate_edit("PR-001", "Milk", Decimal("75.00"))

        sles1 = [s.to_dict() for s in res1["new_sles"]]
        sles2 = [s.to_dict() for s in res2["new_sles"]]
        self.assertEqual(sles1, sles2)

    def test_rate_decrease_reposting(self):
        """Verify behavior when rate decreases from 60 to 40."""
        ledger, _, _ = build_scenario_ledger()
        engine = RepostEngine(ledger)

        # Baseline:
        # PR-001: 50L @ 60 = 3000
        # MFG RM cost: 20*50 + 50*60 + 30*60 = 1000 + 3000 + 1800 = 5800
        # Rate decrease to 40:
        # PR-001: 50L @ 40 = 2000 (-1000)
        # MFG RM cost: 20*50 + 50*40 + 30*60 = 1000 + 2000 + 1800 = 4800
        # Milk Powder incoming rate: 4800 / 10 = 480/Kg (was 580)
        # Milk Powder DN COGS: 10 * 480 = 4800 (was 5800, -1000)
        res = engine.simulate_rate_edit("PR-001", "Milk", Decimal("40.00"))
        new_map = {(s.voucher_no, s.item_code): s for s in res["new_sles"]}

        mfg_powder = new_map[("MFG-001", "Milk Powder")]
        self.assertEqual(mfg_powder.incoming_rate, Decimal("480.0000"))
        dn2 = new_map[("DN-002", "Milk Powder")]
        self.assertEqual(dn2.outgoing_rate, Decimal("480.0000"))
        self.assertEqual(dn2.stock_value_difference, Decimal("-4800.00"))

    def test_dependency_graph_detection(self):
        """Verifies that the engine discovers downstream items produced by manufacturing."""
        ledger, _, _ = build_scenario_ledger()
        engine = RepostEngine(ledger)
        dag = engine.build_dependency_graph("PR-001", "Milk")

        self.assertIn("Milk", dag)
        self.assertIn("Milk Powder", dag["Milk"])


if __name__ == "__main__":
    unittest.main()
