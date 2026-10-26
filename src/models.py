"""
Data models for ERPNext Stock Valuation & Reposting Simulation.
Represents Stock Ledger Entries, Transactions, Items, and General Ledger impact.
"""

from dataclasses import dataclass, field
from datetime import date, time
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import List, Optional, Dict, Any


class ValuationMethod(str, Enum):
    FIFO = "FIFO"
    MOVING_AVERAGE = "Moving Average"


class VoucherType(str, Enum):
    OPENING_STOCK = "Stock Entry - Opening"
    PURCHASE_RECEIPT = "Purchase Receipt"
    DELIVERY_NOTE = "Delivery Note"
    STOCK_ENTRY_MANUFACTURE = "Stock Entry - Manufacture"
    STOCK_ENTRY_TRANSFER = "Stock Entry - Material Transfer"
    PURCHASE_INVOICE = "Purchase Invoice"
    SALES_INVOICE = "Sales Invoice"


@dataclass
class Item:
    item_code: str
    item_name: str
    stock_uom: str
    valuation_method: ValuationMethod = ValuationMethod.FIFO


@dataclass
class StockTransaction:
    """Represents a business document transaction (Voucher) affecting stock."""
    voucher_type: VoucherType
    voucher_no: str
    posting_date: str  # YYYY-MM-DD
    posting_time: str = "12:00:00"
    item_code: str = ""
    warehouse: str = "Stores - TC"
    qty: Decimal = Decimal("0")  # Positive for inward, negative for outward
    rate: Decimal = Decimal("0")  # Inward purchase/production rate or valuation rate
    # For manufacturing / multi-item vouchers:
    consumed_items: List[Dict[str, Any]] = field(default_factory=list)
    produced_items: List[Dict[str, Any]] = field(default_factory=list)
    remarks: str = ""

    def __post_init__(self):
        if not isinstance(self.qty, Decimal):
            self.qty = Decimal(str(self.qty))
        if not isinstance(self.rate, Decimal):
            self.rate = Decimal(str(self.rate))


@dataclass
class StockLedgerEntry:
    """
    Direct representation of ERPNext's `tabStock Ledger Entry` (SLE).
    Stores ledger facts and running balance snapshots.
    """
    name: str
    item_code: str
    warehouse: str
    posting_date: str
    posting_time: str
    voucher_type: VoucherType
    voucher_no: str
    actual_qty: Decimal
    incoming_rate: Decimal = Decimal("0")
    outgoing_rate: Decimal = Decimal("0")
    valuation_rate: Decimal = Decimal("0")
    stock_value_difference: Decimal = Decimal("0")  # Change in inventory value
    qty_after_transaction: Decimal = Decimal("0")  # Running balance qty
    stock_value: Decimal = Decimal("0")            # Running inventory value
    stock_queue: List[List[Decimal]] = field(default_factory=list)  # FIFO queue [[qty, rate], ...]
    is_cancelled: bool = False
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "item_code": self.item_code,
            "warehouse": self.warehouse,
            "posting_date": self.posting_date,
            "voucher_type": self.voucher_type.value,
            "voucher_no": self.voucher_no,
            "actual_qty": float(self.actual_qty),
            "incoming_rate": float(self.incoming_rate),
            "outgoing_rate": float(self.outgoing_rate),
            "stock_value_diff": float(self.stock_value_difference),
            "qty_after_tx": float(self.qty_after_transaction),
            "stock_value": float(self.stock_value),
            "stock_queue": [[float(q), float(r)] for q, r in self.stock_queue]
        }


@dataclass
class GLEntry:
    """Representation of financial impact in `tabGL Entry`."""
    posting_date: str
    voucher_type: VoucherType
    voucher_no: str
    account: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    remarks: str = ""

    def __post_init__(self):
        if not isinstance(self.debit, Decimal):
            self.debit = Decimal(str(self.debit))
        if not isinstance(self.credit, Decimal):
            self.credit = Decimal(str(self.credit))
@dataclass
class RepostItemValuationDoc:
    """
    Representation of ERPNext's `tabRepost Item Valuation` (RIV) document.
    Tracks queued reposting jobs across items, warehouses, and timestamps.
    """
    name: str
    item_code: str
    warehouse: str
    posting_date: str
    posting_time: str
    voucher_type: VoucherType
    voucher_no: str
    status: str = "Queued"  # Queued, In Progress, Completed, Failed
    error_log: str = ""