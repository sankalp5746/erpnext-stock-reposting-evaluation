"""
Reposting Engine for ERPNext.
Simulates Repost Item Valuation (RIV), dependency DAG traversal,
and diff calculation across SLEs and GL Entries.
"""

from decimal import Decimal
from typing import Dict, List, Optional, Set, Tuple, Any
from .models import (
    StockTransaction,
    StockLedgerEntry,
    VoucherType,
    GLEntry,
    RepostItemValuationDoc
)
from .ledger import StockLedger
from .gl_mapper import GLMapper


class RepostEngine:
    """
    Manages valuation recalculation and cross-item dependency cascading.
    Mimics ERPNext's `erpnext.stock.doctype.repost_item_valuation`.
    """

    def __init__(self, ledger: StockLedger, gl_mapper: Optional[GLMapper] = None):
        self.ledger = ledger
        self.gl_mapper = gl_mapper or GLMapper()
        self.repost_logs: List[RepostItemValuationDoc] = []

    def build_dependency_graph(
        self,
        modified_voucher_no: str,
        modified_item_code: str
    ) -> Dict[str, Set[str]]:
        """
        Builds a Directed Acyclic Graph (DAG) of affected items and vouchers.
        Identifies downstream manufacturing transformations (RM -> FG).
        """
        item_dependencies: Dict[str, Set[str]] = {modified_item_code: set()}
        voucher_dependencies: Set[str] = {modified_voucher_no}

        # Scan for manufacturing vouchers where modified item is consumed
        for tx in self.ledger.transactions:
            if tx.voucher_type == VoucherType.STOCK_ENTRY_MANUFACTURE:
                consumed_codes = {rm["item_code"] for rm in tx.consumed_items}
                produced_codes = {fg["item_code"] for fg in tx.produced_items}

                # If this voucher consumes an affected item, its produced items are affected
                for aff_item in list(item_dependencies.keys()):
                    if aff_item in consumed_codes:
                        voucher_dependencies.add(tx.voucher_no)
                        for fg_code in produced_codes:
                            if fg_code not in item_dependencies:
                                item_dependencies[fg_code] = set()
                            item_dependencies[aff_item].add(fg_code)

        return item_dependencies

    def simulate_rate_edit(
        self,
        voucher_no: str,
        item_code: str,
        new_rate: Decimal
    ) -> Dict[str, Any]:
        """
        Simulates editing the incoming rate of a past transaction and triggers reposting.
        Returns a comprehensive report showing:
        - Old SLEs vs New SLEs
        - Affected vouchers and items
        - GL Entry differences (Stock In Hand, COGS, Liability)
        """
        # Step 1: Snapshot baseline state
        old_sles = [sle for sle in self.ledger.stock_ledger_entries]
        old_gl_entries: List[GLEntry] = []
        for sle in old_sles:
            old_gl_entries.extend(self.gl_mapper.generate_gl_entries(sle))

        # Step 2: Locate target transaction and update rate
        target_tx: Optional[StockTransaction] = None
        for tx in self.ledger.transactions:
            if tx.voucher_no == voucher_no and tx.item_code == item_code:
                target_tx = tx
                break

        if not target_tx:
            raise ValueError(f"Transaction {voucher_no} for item {item_code} not found!")

        old_rate = target_tx.rate
        target_tx.rate = Decimal(str(new_rate))

        # Step 3: Record Repost Item Valuation document
        riv = RepostItemValuationDoc(
            name=f"RIV-{len(self.repost_logs)+1:04d}",
            item_code=item_code,
            warehouse=target_tx.warehouse,
            posting_date=target_tx.posting_date,
            posting_time=target_tx.posting_time,
            voucher_type=target_tx.voucher_type,
            voucher_no=target_tx.voucher_no,
            status="In Progress"
        )
        self.repost_logs.append(riv)

        # Step 4: Re-process all transactions forward
        new_sles = self.ledger.process_all()
        new_gl_entries: List[GLEntry] = []
        for sle in new_sles:
            new_gl_entries.extend(self.gl_mapper.generate_gl_entries(sle))

        riv.status = "Completed"

        # Step 5: Compute detailed diffs
        sle_diffs = self._diff_sles(old_sles, new_sles)
        gl_diffs = self._diff_gl(old_gl_entries, new_gl_entries)

        dep_graph = self.build_dependency_graph(voucher_no, item_code)

        return {
            "voucher_no": voucher_no,
            "item_code": item_code,
            "old_rate": float(old_rate),
            "new_rate": float(new_rate),
            "affected_items": list(dep_graph.keys()),
            "dependency_graph": {k: list(v) for k, v in dep_graph.items()},
            "sle_diffs": sle_diffs,
            "gl_diffs": gl_diffs,
            "old_sles": old_sles,
            "new_sles": new_sles,
            "old_gl_entries": old_gl_entries,
            "new_gl_entries": new_gl_entries
        }

    def _diff_sles(
        self,
        old_sles: List[StockLedgerEntry],
        new_sles: List[StockLedgerEntry]
    ) -> List[Dict[str, Any]]:
        """Identifies changes between before and after SLEs."""
        diffs = []
        # Match by (voucher_type, voucher_no, item_code)
        old_map = {(s.voucher_type, s.voucher_no, s.item_code): s for s in old_sles}
        new_map = {(s.voucher_type, s.voucher_no, s.item_code): s for s in new_sles}

        for key, new_sle in new_map.items():
            old_sle = old_map.get(key)
            if not old_sle:
                diffs.append({
                    "voucher_no": new_sle.voucher_no,
                    "item_code": new_sle.item_code,
                    "change_type": "NEW",
                    "details": "Newly generated entry"
                })
                continue

            rate_changed = (
                old_sle.incoming_rate != new_sle.incoming_rate or
                old_sle.outgoing_rate != new_sle.outgoing_rate
            )
            val_diff_changed = (old_sle.stock_value_difference != new_sle.stock_value_difference)
            running_val_changed = (old_sle.stock_value != new_sle.stock_value)
            queue_changed = (old_sle.stock_queue != new_sle.stock_queue)

            if rate_changed or val_diff_changed or running_val_changed or queue_changed:
                diffs.append({
                    "voucher_no": new_sle.voucher_no,
                    "voucher_type": new_sle.voucher_type.value,
                    "item_code": new_sle.item_code,
                    "posting_date": new_sle.posting_date,
                    "actual_qty": float(new_sle.actual_qty),
                    "old_incoming_rate": float(old_sle.incoming_rate),
                    "new_incoming_rate": float(new_sle.incoming_rate),
                    "old_outgoing_rate": float(old_sle.outgoing_rate),
                    "new_outgoing_rate": float(new_sle.outgoing_rate),
                    "old_stock_value_diff": float(old_sle.stock_value_difference),
                    "new_stock_value_diff": float(new_sle.stock_value_difference),
                    "delta_stock_value_diff": float(new_sle.stock_value_difference - old_sle.stock_value_difference),
                    "old_running_val": float(old_sle.stock_value),
                    "new_running_val": float(new_sle.stock_value),
                    "old_queue": [[float(q), float(r)] for q, r in old_sle.stock_queue],
                    "new_queue": [[float(q), float(r)] for q, r in new_sle.stock_queue],
                })
        return diffs

    def _diff_gl(
        self,
        old_gl: List[GLEntry],
        new_gl: List[GLEntry]
    ) -> List[Dict[str, Any]]:
        """Calculates adjustment GL entries needed to reconcile the books."""
        # Sum by account
        old_acc: Dict[str, Decimal] = {}
        new_acc: Dict[str, Decimal] = {}

        for g in old_gl:
            net = g.debit - g.credit
            old_acc[g.account] = old_acc.get(g.account, Decimal("0")) + net

        for g in new_gl:
            net = g.debit - g.credit
            new_acc[g.account] = new_acc.get(g.account, Decimal("0")) + net

        all_accounts = set(old_acc.keys()).union(new_acc.keys())
        diffs = []
        for acc in sorted(all_accounts):
            old_net = old_acc.get(acc, Decimal("0"))
            new_net = new_acc.get(acc, Decimal("0"))
            delta = new_net - old_net
            if delta != Decimal("0"):
                diffs.append({
                    "account": acc,
                    "old_net": float(old_net),
                    "new_net": float(new_net),
                    "adjustment_delta": float(delta)
                })
        return diffs
