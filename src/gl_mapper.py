"""
General Ledger (GL) mapper for ERPNext Perpetual Inventory system.
Maps Stock Ledger changes to accounting ledger entries (Stock In Hand, COGS, etc.).
"""

from decimal import Decimal
from typing import List
from .models import GLEntry, StockLedgerEntry, VoucherType


class GLMapper:
    """Generates double-entry accounting records from Stock Ledger Entries."""

    def __init__(self, company_abbr: str = "TC"):
        self.stock_in_hand_account = f"Stock In Hand - {company_abbr}"
        self.cogs_account = f"Cost of Goods Sold - {company_abbr}"
        self.stock_received_but_not_billed = f"Stock Received But Not Billed - {company_abbr}"
        self.stock_adjustment_account = f"Stock Adjustment - {company_abbr}"

    def generate_gl_entries(self, sle: StockLedgerEntry) -> List[GLEntry]:
        """Maps a single Stock Ledger Entry to its corresponding balanced GL Entries."""
        entries: List[GLEntry] = []
        abs_val_diff = abs(sle.stock_value_difference)

        if abs_val_diff == Decimal("0"):
            return entries

        if sle.voucher_type == VoucherType.OPENING_STOCK:
            # Debit Stock In Hand, Credit Stock Adjustment / Opening
            entries.append(
                GLEntry(
                    posting_date=sle.posting_date,
                    voucher_type=sle.voucher_type,
                    voucher_no=sle.voucher_no,
                    account=self.stock_in_hand_account,
                    debit=abs_val_diff,
                    credit=Decimal("0"),
                    remarks=f"Opening stock for {sle.item_code}"
                )
            )
            entries.append(
                GLEntry(
                    posting_date=sle.posting_date,
                    voucher_type=sle.voucher_type,
                    voucher_no=sle.voucher_no,
                    account=self.stock_adjustment_account,
                    debit=Decimal("0"),
                    credit=abs_val_diff,
                    remarks=f"Opening stock offset for {sle.item_code}"
                )
            )

        elif sle.voucher_type == VoucherType.PURCHASE_RECEIPT:
            # Incoming: Debit Stock In Hand, Credit Stock Received But Not Billed
            entries.append(
                GLEntry(
                    posting_date=sle.posting_date,
                    voucher_type=sle.voucher_type,
                    voucher_no=sle.voucher_no,
                    account=self.stock_in_hand_account,
                    debit=abs_val_diff,
                    credit=Decimal("0"),
                    remarks=f"Stock receipt for {sle.item_code} ({sle.actual_qty} @ ₹{sle.incoming_rate})"
                )
            )
            entries.append(
                GLEntry(
                    posting_date=sle.posting_date,
                    voucher_type=sle.voucher_type,
                    voucher_no=sle.voucher_no,
                    account=self.stock_received_but_not_billed,
                    debit=Decimal("0"),
                    credit=abs_val_diff,
                    remarks=f"Stock received liability for {sle.item_code}"
                )
            )

        elif sle.voucher_type == VoucherType.DELIVERY_NOTE:
            # Outgoing: Debit COGS, Credit Stock In Hand
            entries.append(
                GLEntry(
                    posting_date=sle.posting_date,
                    voucher_type=sle.voucher_type,
                    voucher_no=sle.voucher_no,
                    account=self.cogs_account,
                    debit=abs_val_diff,
                    credit=Decimal("0"),
                    remarks=f"COGS recognized on delivery of {sle.item_code} ({abs(sle.actual_qty)} @ ₹{sle.outgoing_rate})"
                )
            )
            entries.append(
                GLEntry(
                    posting_date=sle.posting_date,
                    voucher_type=sle.voucher_type,
                    voucher_no=sle.voucher_no,
                    account=self.stock_in_hand_account,
                    debit=Decimal("0"),
                    credit=abs_val_diff,
                    remarks=f"Stock reduction on delivery of {sle.item_code}"
                )
            )

        elif sle.voucher_type == VoucherType.STOCK_ENTRY_MANUFACTURE:
            if sle.actual_qty < Decimal("0"):
                # Raw material consumed: Credit Stock In Hand
                entries.append(
                    GLEntry(
                        posting_date=sle.posting_date,
                        voucher_type=sle.voucher_type,
                        voucher_no=sle.voucher_no,
                        account=self.stock_in_hand_account,
                        debit=Decimal("0"),
                        credit=abs_val_diff,
                        remarks=f"Raw material consumed: {sle.item_code}"
                    )
                )
            else:
                # Finished goods produced: Debit Stock In Hand
                entries.append(
                    GLEntry(
                        posting_date=sle.posting_date,
                        voucher_type=sle.voucher_type,
                        voucher_no=sle.voucher_no,
                        account=self.stock_in_hand_account,
                        debit=abs_val_diff,
                        credit=Decimal("0"),
                        remarks=f"Finished goods produced: {sle.item_code} ({sle.actual_qty} @ ₹{sle.incoming_rate})"
                    )
                )

        return entries
