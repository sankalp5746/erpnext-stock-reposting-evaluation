"""
Stock Ledger implementation for ERPNext.
Handles forward chronological evaluation of stock queues, valuation rates,
multi-item manufacturing transfers, and stock ledger entries.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Tuple, Any
from .models import (
    Item,
    StockTransaction,
    StockLedgerEntry,
    VoucherType,
    ValuationMethod
)
from .fifo_queue import FIFOQueue, quantize_currency, quantize_rate


class StockLedger:
    """
    Simulates ERPNext's Stock Ledger engine.
    Maintains chronological transaction logs and builds SLE snapshots.
    """

    def __init__(self):
        self.items: Dict[str, Item] = {}
        self.transactions: List[StockTransaction] = []
        self.stock_ledger_entries: List[StockLedgerEntry] = []
        self._sle_counter: int = 1

    def register_item(self, item: Item) -> None:
        self.items[item.item_code] = item

    def add_transaction(self, tx: StockTransaction) -> None:
        self.transactions.append(tx)

    def sort_transactions(self) -> None:
        """Sorts transactions chronologically by posting_date, posting_time, and voucher_no."""
        self.transactions.sort(key=lambda x: (x.posting_date, x.posting_time, x.voucher_no))

    def process_all(self) -> List[StockLedgerEntry]:
        """
        Executes a complete forward pass over all transactions chronologically.
        Computes FIFO queues, running balances, and outputs StockLedgerEntries.
        """
        self.sort_transactions()
        self.stock_ledger_entries = []
        self._sle_counter = 1

        # State tracking: (item_code, warehouse) -> FIFOQueue
        queues: Dict[Tuple[str, str], FIFOQueue] = {}
        running_qty: Dict[Tuple[str, str], Decimal] = {}
        running_value: Dict[Tuple[str, str], Decimal] = {}

        for tx in self.transactions:
            if tx.voucher_type == VoucherType.STOCK_ENTRY_MANUFACTURE:
                # Handle multi-item manufacturing entry
                self._process_manufacture_tx(tx, queues, running_qty, running_value)
            else:
                # Standard single-item transaction
                self._process_single_tx(tx, queues, running_qty, running_value)

        return self.stock_ledger_entries

    def _get_queue(self, item_code: str, warehouse: str, queues: Dict[Tuple[str, str], FIFOQueue]) -> FIFOQueue:
        key = (item_code, warehouse)
        if key not in queues:
            queues[key] = FIFOQueue()
        return queues[key]

    def _process_single_tx(
        self,
        tx: StockTransaction,
        queues: Dict[Tuple[str, str], FIFOQueue],
        running_qty: Dict[Tuple[str, str], Decimal],
        running_value: Dict[Tuple[str, str], Decimal]
    ) -> None:
        key = (tx.item_code, tx.warehouse)
        queue = self._get_queue(tx.item_code, tx.warehouse, queues)
        prev_qty = running_qty.get(key, Decimal("0"))
        prev_val = running_value.get(key, Decimal("0"))

        sle_name = f"SLE-{self._sle_counter:04d}"
        self._sle_counter += 1

        if tx.qty > Decimal("0"):
            # Inward transaction (Purchase Receipt, Opening Stock, etc.)
            incoming_rate = tx.rate
            val_diff = tx.qty * incoming_rate
            queue.add(tx.qty, incoming_rate)

            new_qty = prev_qty + tx.qty
            new_val = prev_val + val_diff
            val_rate = new_val / new_qty if new_qty > Decimal("0") else Decimal("0")

            sle = StockLedgerEntry(
                name=sle_name,
                item_code=tx.item_code,
                warehouse=tx.warehouse,
                posting_date=tx.posting_date,
                posting_time=tx.posting_time,
                voucher_type=tx.voucher_type,
                voucher_no=tx.voucher_no,
                actual_qty=tx.qty,
                incoming_rate=incoming_rate,
                outgoing_rate=Decimal("0"),
                valuation_rate=quantize_rate(val_rate),
                stock_value_difference=quantize_currency(val_diff),
                qty_after_transaction=new_qty,
                stock_value=quantize_currency(new_val),
                stock_queue=queue.to_list()
            )
            running_qty[key] = new_qty
            running_value[key] = new_val
            self.stock_ledger_entries.append(sle)

        elif tx.qty < Decimal("0"):
            # Outward transaction (Delivery Note, Material Issue, etc.)
            consume_qty = abs(tx.qty)
            consumed_val, breakdown = queue.consume(consume_qty)
            outgoing_rate = consumed_val / consume_qty if consume_qty > Decimal("0") else Decimal("0")
            val_diff = -consumed_val

            new_qty = prev_qty - consume_qty
            new_val = prev_val - consumed_val
            val_rate = new_val / new_qty if new_qty > Decimal("0") else Decimal("0")

            sle = StockLedgerEntry(
                name=sle_name,
                item_code=tx.item_code,
                warehouse=tx.warehouse,
                posting_date=tx.posting_date,
                posting_time=tx.posting_time,
                voucher_type=tx.voucher_type,
                voucher_no=tx.voucher_no,
                actual_qty=tx.qty,
                incoming_rate=Decimal("0"),
                outgoing_rate=quantize_rate(outgoing_rate),
                valuation_rate=quantize_rate(val_rate),
                stock_value_difference=quantize_currency(val_diff),
                qty_after_transaction=new_qty,
                stock_value=quantize_currency(new_val),
                stock_queue=queue.to_list()
            )
            running_qty[key] = new_qty
            running_value[key] = new_val
            self.stock_ledger_entries.append(sle)

    def _process_manufacture_tx(
        self,
        tx: StockTransaction,
        queues: Dict[Tuple[str, str], FIFOQueue],
        running_qty: Dict[Tuple[str, str], Decimal],
        running_value: Dict[Tuple[str, str], Decimal]
    ) -> None:
        """
        Processes a Stock Entry (Manufacture):
        1. Consumes raw materials from queue, calculating total raw material cost.
        2. Transfers cost to produced items, computing incoming rate.
        3. Appends produced items to finished goods queue.
        """
        total_rm_cost = Decimal("0")

        # Step 1: Consume raw materials
        for rm in tx.consumed_items:
            rm_item_code = rm["item_code"]
            rm_wh = rm.get("warehouse", tx.warehouse)
            rm_qty = Decimal(str(rm["qty"]))
            key = (rm_item_code, rm_wh)
            queue = self._get_queue(rm_item_code, rm_wh, queues)

            prev_qty = running_qty.get(key, Decimal("0"))
            prev_val = running_value.get(key, Decimal("0"))

            consumed_val, breakdown = queue.consume(rm_qty)
            outgoing_rate = consumed_val / rm_qty
            val_diff = -consumed_val
            total_rm_cost += consumed_val

            new_qty = prev_qty - rm_qty
            new_val = prev_val - consumed_val
            val_rate = new_val / new_qty if new_qty > Decimal("0") else Decimal("0")

            sle_name = f"SLE-{self._sle_counter:04d}"
            self._sle_counter += 1

            sle = StockLedgerEntry(
                name=sle_name,
                item_code=rm_item_code,
                warehouse=rm_wh,
                posting_date=tx.posting_date,
                posting_time=tx.posting_time,
                voucher_type=tx.voucher_type,
                voucher_no=tx.voucher_no,
                actual_qty=-rm_qty,
                incoming_rate=Decimal("0"),
                outgoing_rate=quantize_rate(outgoing_rate),
                valuation_rate=quantize_rate(val_rate),
                stock_value_difference=quantize_currency(val_diff),
                qty_after_transaction=new_qty,
                stock_value=quantize_currency(new_val),
                stock_queue=queue.to_list()
            )
            running_qty[key] = new_qty
            running_value[key] = new_val
            self.stock_ledger_entries.append(sle)

        # Step 2: Produce finished goods
        # Cost of raw materials is distributed across produced items
        total_produced_qty = sum(Decimal(str(p["qty"])) for p in tx.produced_items)

        for fg in tx.produced_items:
            fg_item_code = fg["item_code"]
            fg_wh = fg.get("warehouse", tx.warehouse)
            fg_qty = Decimal(str(fg["qty"]))
            key = (fg_item_code, fg_wh)
            queue = self._get_queue(fg_item_code, fg_wh, queues)

            prev_qty = running_qty.get(key, Decimal("0"))
            prev_val = running_value.get(key, Decimal("0"))

            # Incoming rate derived from consumed RM cost
            fg_share = fg_qty / total_produced_qty if total_produced_qty > Decimal("0") else Decimal("1")
            fg_cost = total_rm_cost * fg_share
            incoming_rate = fg_cost / fg_qty

            val_diff = fg_cost
            queue.add(fg_qty, incoming_rate)

            new_qty = prev_qty + fg_qty
            new_val = prev_val + val_diff
            val_rate = new_val / new_qty if new_qty > Decimal("0") else Decimal("0")

            sle_name = f"SLE-{self._sle_counter:04d}"
            self._sle_counter += 1

            sle = StockLedgerEntry(
                name=sle_name,
                item_code=fg_item_code,
                warehouse=fg_wh,
                posting_date=tx.posting_date,
                posting_time=tx.posting_time,
                voucher_type=tx.voucher_type,
                voucher_no=tx.voucher_no,
                actual_qty=fg_qty,
                incoming_rate=quantize_rate(incoming_rate),
                outgoing_rate=Decimal("0"),
                valuation_rate=quantize_rate(val_rate),
                stock_value_difference=quantize_currency(val_diff),
                qty_after_transaction=new_qty,
                stock_value=quantize_currency(new_val),
                stock_queue=queue.to_list()
            )
            running_qty[key] = new_qty
            running_value[key] = new_val
            self.stock_ledger_entries.append(sle)

    def get_entries_for_item(self, item_code: str) -> List[StockLedgerEntry]:
        return [sle for sle in self.stock_ledger_entries if sle.item_code == item_code]
