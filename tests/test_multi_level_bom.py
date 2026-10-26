"""
Unit tests validating multi-tier manufacturing BOM cascade.
Raw Milk -> Milk Cream -> Butter
Rate edits at the bottom layer must cascade to intermediate and top tiers!
"""

import unittest
from decimal import Decimal
from src.models import Item, StockTransaction, VoucherType, ValuationMethod
from src.ledger import StockLedger
from src.repost_engine import RepostEngine


class TestMultiLevelBOM(unittest.TestCase):

    def test_three_tier_manufacturing_cascade(self):
        ledger = StockLedger()

        raw_milk = Item(item_code="Raw Milk", item_name="Raw Milk", stock_uom="Litre")
        cream = Item(item_code="Milk Cream", item_name="Milk Cream", stock_uom="Litre")
        butter = Item(item_code="Butter", item_name="Pasteurized Butter", stock_uom="Kg")

        ledger.register_item(raw_milk)
        ledger.register_item(cream)
        ledger.register_item(butter)

        # Tier 1: Purchase Raw Milk (100L @ 40)
        ledger.add_transaction(StockTransaction(
            voucher_type=VoucherType.PURCHASE_RECEIPT,
            voucher_no="PR-RAW-01",
            posting_date="2026-02-01",
            item_code="Raw Milk",
            qty=Decimal("100"),
            rate=Decimal("40.00")
        ))

        # Tier 2: Manufacture Cream from Raw Milk (100L Raw Milk -> 20L Cream)
        ledger.add_transaction(StockTransaction(
            voucher_type=VoucherType.STOCK_ENTRY_MANUFACTURE,
            voucher_no="MFG-CREAM-01",
            posting_date="2026-02-02",
            consumed_items=[{"item_code": "Raw Milk", "qty": Decimal("100")}],
            produced_items=[{"item_code": "Milk Cream", "qty": Decimal("20")}]
        ))

        # Tier 3: Manufacture Butter from Cream (20L Cream -> 5 Kg Butter)
        ledger.add_transaction(StockTransaction(
            voucher_type=VoucherType.STOCK_ENTRY_MANUFACTURE,
            voucher_no="MFG-BUTTER-01",
            posting_date="2026-02-03",
            consumed_items=[{"item_code": "Milk Cream", "qty": Decimal("20")}],
            produced_items=[{"item_code": "Butter", "qty": Decimal("5")}]
        ))

        # Tier 4: Delivery of Butter (5 Kg Butter)
        ledger.add_transaction(StockTransaction(
            voucher_type=VoucherType.DELIVERY_NOTE,
            voucher_no="DN-BUTTER-01",
            posting_date="2026-02-04",
            item_code="Butter",
            qty=Decimal("-5"),
            rate=Decimal("0")
        ))

        # Initial pass:
        # Raw milk cost: 100 * 40 = 4,000
        # Cream cost: 4,000 / 20 = 200/L
        # Butter cost: (20 * 200) / 5 = 4,000 / 5 = 800/Kg
        # Butter DN COGS: 5 * 800 = 4,000
        initial_sles = ledger.process_all()
        sle_map = {(s.voucher_no, s.item_code): s for s in initial_sles}
        self.assertEqual(sle_map[("DN-BUTTER-01", "Butter")].outgoing_rate, Decimal("800.0000"))

        # Edit Tier 1 Raw Milk incoming rate from 40 to 60 (+50%)
        repost_engine = RepostEngine(ledger)
        result = repost_engine.simulate_rate_edit(
            voucher_no="PR-RAW-01",
            item_code="Raw Milk",
            new_rate=Decimal("60.00")
        )

        new_map = {(s.voucher_no, s.item_code): s for s in result["new_sles"]}

        # New calculations:
        # Raw milk cost: 100 * 60 = 6,000
        # Cream incoming rate: 6,000 / 20 = 300/L (was 200)
        # Butter incoming rate: 6,000 / 5 = 1,200/Kg (was 800)
        # Butter Delivery Note COGS: 5 * 1200 = 6,000 (was 4,000)
        self.assertEqual(new_map[("MFG-CREAM-01", "Milk Cream")].incoming_rate, Decimal("300.0000"))
        self.assertEqual(new_map[("MFG-BUTTER-01", "Butter")].incoming_rate, Decimal("1200.0000"))
        self.assertEqual(new_map[("DN-BUTTER-01", "Butter")].outgoing_rate, Decimal("1200.0000"))
        self.assertEqual(new_map[("DN-BUTTER-01", "Butter")].stock_value_difference, Decimal("-6000.00"))


if __name__ == "__main__":
    unittest.main()
