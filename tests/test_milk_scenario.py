"""
Unit tests validating the exact scenario from the assignment:
- Milk opening stock: 100L @ 50
- 10th Jan PR: 50L @ 60
- 15th Jan DN: 80L
- 20th Jan PR: 50L @ 60
- 21st Jan MFG: 100L Milk -> 10 Kg Milk Powder
- 25th Jan DN: 10 Kg Milk Powder
- Rate edit on 10th Jan PR from 60 to 80.
"""

import unittest
from decimal import Decimal
from src.models import Item, StockTransaction, VoucherType, ValuationMethod
from src.ledger import StockLedger
from src.repost_engine import RepostEngine
from src.demo import build_scenario_ledger


class TestMilkScenario(unittest.TestCase):

    def setUp(self):
        self.ledger, self.milk, self.milk_powder = build_scenario_ledger()
        self.baseline_sles = self.ledger.process_all()
        self.repost_engine = RepostEngine(self.ledger)

    def test_baseline_valuation_before_edit(self):
        """Verifies initial state calculations before any user edits."""
        sle_map = {(s.voucher_no, s.item_code): s for s in self.baseline_sles}

        # 1. Opening stock
        op = sle_map[("OPENING-001", "Milk")]
        self.assertEqual(op.actual_qty, Decimal("100"))
        self.assertEqual(op.incoming_rate, Decimal("50.00"))
        self.assertEqual(op.stock_value, Decimal("5000.00"))

        # 2. 10th Jan PR
        pr1 = sle_map[("PR-001", "Milk")]
        self.assertEqual(pr1.actual_qty, Decimal("50"))
        self.assertEqual(pr1.incoming_rate, Decimal("60.00"))
        self.assertEqual(pr1.stock_value, Decimal("8000.00"))

        # 3. 15th Jan Milk DN (80L)
        dn1 = sle_map[("DN-001", "Milk")]
        self.assertEqual(dn1.actual_qty, Decimal("-80"))
        self.assertEqual(dn1.outgoing_rate, Decimal("50.0000"))
        self.assertEqual(dn1.stock_value_difference, Decimal("-4000.00"))
        self.assertEqual(dn1.stock_value, Decimal("4000.00"))

        # 4. 20th Jan PR
        pr2 = sle_map[("PR-002", "Milk")]
        self.assertEqual(pr2.actual_qty, Decimal("50"))
        self.assertEqual(pr2.incoming_rate, Decimal("60.00"))
        self.assertEqual(pr2.stock_value, Decimal("7000.00"))

        # 5. 21st Jan Manufacture Entry
        mfg_milk = sle_map[("MFG-001", "Milk")]
        self.assertEqual(mfg_milk.actual_qty, Decimal("-100"))
        self.assertEqual(mfg_milk.outgoing_rate, Decimal("58.0000"))
        self.assertEqual(mfg_milk.stock_value_difference, Decimal("-5800.00"))
        self.assertEqual(mfg_milk.stock_value, Decimal("1200.00"))

        mfg_powder = sle_map[("MFG-001", "Milk Powder")]
        self.assertEqual(mfg_powder.actual_qty, Decimal("10"))
        self.assertEqual(mfg_powder.incoming_rate, Decimal("580.0000"))
        self.assertEqual(mfg_powder.stock_value, Decimal("5800.00"))

        # 6. 25th Jan Milk Powder DN
        dn2 = sle_map[("DN-002", "Milk Powder")]
        self.assertEqual(dn2.actual_qty, Decimal("-10"))
        self.assertEqual(dn2.outgoing_rate, Decimal("580.0000"))
        self.assertEqual(dn2.stock_value_difference, Decimal("-5800.00"))
        self.assertEqual(dn2.stock_value, Decimal("0.00"))

    def test_reposting_after_rate_change_from_60_to_80(self):
        """Verifies recalculation after changing 10th Jan PR rate from 60 to 80."""
        result = self.repost_engine.simulate_rate_edit(
            voucher_no="PR-001",
            item_code="Milk",
            new_rate=Decimal("80.00")
        )

        new_map = {(s.voucher_no, s.item_code): s for s in result["new_sles"]}

        # 1. 10th Jan PR: rate changed to 80, stock value difference 4,000 (was 3,000)
        pr1 = new_map[("PR-001", "Milk")]
        self.assertEqual(pr1.incoming_rate, Decimal("80.00"))
        self.assertEqual(pr1.stock_value_difference, Decimal("4000.00"))
        self.assertEqual(pr1.stock_value, Decimal("9000.00"))

        # 2. 15th Jan Milk DN (80L): Outgoing rate must REMAIN 50 (from opening stock), COGS unchanged!
        dn1 = new_map[("DN-001", "Milk")]
        self.assertEqual(dn1.outgoing_rate, Decimal("50.0000"))
        self.assertEqual(dn1.stock_value_difference, Decimal("-4000.00"))
        # But running balance reflects the higher value in the remaining queue
        self.assertEqual(dn1.stock_value, Decimal("5000.00"))  # was 4,000.00

        # 3. 20th Jan PR: incoming rate unchanged at 60, but running balance is +1,000
        pr2 = new_map[("PR-002", "Milk")]
        self.assertEqual(pr2.incoming_rate, Decimal("60.00"))
        self.assertEqual(pr2.stock_value, Decimal("8000.00"))  # was 7,000.00

        # 4. 21st Jan Manufacture:
        # 100L consumed breakdown:
        # - 20L @ 50 = 1000
        # - 50L @ 80 = 4000 (was 50 @ 60 = 3000)
        # - 30L @ 60 = 1800
        # Total RM cost = 6,800 (was 5,800, +1,000)
        mfg_milk = new_map[("MFG-001", "Milk")]
        self.assertEqual(mfg_milk.outgoing_rate, Decimal("68.0000"))
        self.assertEqual(mfg_milk.stock_value_difference, Decimal("-6800.00"))
        self.assertEqual(mfg_milk.stock_value, Decimal("1200.00"))

        # Finished good production cost transfer:
        # 10 Kg Milk Powder produced at 6,800 / 10 = 680/Kg (was 580/Kg)
        mfg_powder = new_map[("MFG-001", "Milk Powder")]
        self.assertEqual(mfg_powder.incoming_rate, Decimal("680.0000"))
        self.assertEqual(mfg_powder.stock_value_difference, Decimal("6800.00"))
        self.assertEqual(mfg_powder.stock_value, Decimal("6800.00"))

        # 5. 25th Jan Milk Powder DN:
        # Outgoing 10 Kg @ 680/Kg = 6,800 COGS (was 5,800 COGS, +1,000)
        dn2 = new_map[("DN-002", "Milk Powder")]
        self.assertEqual(dn2.outgoing_rate, Decimal("680.0000"))
        self.assertEqual(dn2.stock_value_difference, Decimal("-6800.00"))
        self.assertEqual(dn2.stock_value, Decimal("0.00"))

        # 6. GL Impact: COGS increased by exactly 1,000
        gl_diff_map = {g["account"]: g["adjustment_delta"] for g in result["gl_diffs"]}
        self.assertEqual(gl_diff_map["Cost of Goods Sold - TC"], 1000.0)
        self.assertEqual(gl_diff_map["Stock Received But Not Billed - TC"], -1000.0)


if __name__ == "__main__":
    unittest.main()
