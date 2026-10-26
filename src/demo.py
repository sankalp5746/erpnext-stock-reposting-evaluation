"""
Interactive demonstration of the ERPNext Stock Reposting and Valuation scenario.
Simulates the exact Milk & Milk Powder lifecycle before and after rate edit.
"""

import sys
from decimal import Decimal
from typing import List, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from .models import Item, StockTransaction, VoucherType, ValuationMethod, StockLedgerEntry
from .ledger import StockLedger
from .repost_engine import RepostEngine
from .gl_mapper import GLMapper


def print_header(title: str):
    print("\n" + "=" * 90)
    print(f"  {title.upper()}")
    print("=" * 90)


def print_table(headers: List[str], rows: List[List[str]], col_widths: List[int]):
    # Format line
    header_line = " | ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    sep_line = "-+-".join("-" * col_widths[i] for i in range(len(headers)))
    print(header_line)
    print(sep_line)
    for row in rows:
        row_line = " | ".join(f"{str(cell):<{col_widths[i]}}" for i, cell in enumerate(row))
        print(row_line)


def format_queue(queue_list: List[List[Decimal]]) -> str:
    if not queue_list:
        return "[]"
    parts = [f"[{float(q):g} @ ₹{float(r):g}]" for q, r in queue_list]
    return ", ".join(parts)


def build_scenario_ledger() -> Tuple[StockLedger, Item, Item]:
    ledger = StockLedger()

    milk = Item(item_code="Milk", item_name="Fresh Cow Milk", stock_uom="Litre", valuation_method=ValuationMethod.FIFO)
    milk_powder = Item(item_code="Milk Powder", item_name="Dehydrated Milk Powder", stock_uom="Kg", valuation_method=ValuationMethod.FIFO)

    ledger.register_item(milk)
    ledger.register_item(milk_powder)

    # 1. Opening stock for Milk: 100L @ ₹50/L (Assume Jan 01)
    ledger.add_transaction(StockTransaction(
        voucher_type=VoucherType.OPENING_STOCK,
        voucher_no="OPENING-001",
        posting_date="2026-01-01",
        posting_time="09:00:00",
        item_code="Milk",
        warehouse="Stores - TC",
        qty=Decimal("100"),
        rate=Decimal("50.00"),
        remarks="Opening stock"
    ))

    # 2. 10th January: Milk Purchase Receipt of 50L @ ₹60/L
    ledger.add_transaction(StockTransaction(
        voucher_type=VoucherType.PURCHASE_RECEIPT,
        voucher_no="PR-001",
        posting_date="2026-01-10",
        posting_time="10:00:00",
        item_code="Milk",
        warehouse="Stores - TC",
        qty=Decimal("50"),
        rate=Decimal("60.00"),
        remarks="Supplier Milk Delivery"
    ))

    # 3. 15th January: Milk Delivery Note of 80L
    ledger.add_transaction(StockTransaction(
        voucher_type=VoucherType.DELIVERY_NOTE,
        voucher_no="DN-001",
        posting_date="2026-01-15",
        posting_time="11:30:00",
        item_code="Milk",
        warehouse="Stores - TC",
        qty=Decimal("-80"),
        rate=Decimal("0"),  # Computed by FIFO
        remarks="Milk dispatch to customer"
    ))

    # 4. 20th January: Milk Purchase Receipt of 50L @ ₹60/L
    ledger.add_transaction(StockTransaction(
        voucher_type=VoucherType.PURCHASE_RECEIPT,
        voucher_no="PR-002",
        posting_date="2026-01-20",
        posting_time="14:00:00",
        item_code="Milk",
        warehouse="Stores - TC",
        qty=Decimal("50"),
        rate=Decimal("60.00"),
        remarks="Second Milk Delivery"
    ))

    # 5. 21st January: Manufacture Entry: 100L Milk Consume and 10 Kg Milk Powder Produced
    ledger.add_transaction(StockTransaction(
        voucher_type=VoucherType.STOCK_ENTRY_MANUFACTURE,
        voucher_no="MFG-001",
        posting_date="2026-01-21",
        posting_time="16:00:00",
        consumed_items=[
            {"item_code": "Milk", "warehouse": "Stores - TC", "qty": Decimal("100")}
        ],
        produced_items=[
            {"item_code": "Milk Powder", "warehouse": "Stores - TC", "qty": Decimal("10")}
        ],
        remarks="Convert 100L Milk into 10 Kg Milk Powder"
    ))

    # 6. 25th January: Milk Powder Delivery Note of 10 KG
    ledger.add_transaction(StockTransaction(
        voucher_type=VoucherType.DELIVERY_NOTE,
        voucher_no="DN-002",
        posting_date="2026-01-25",
        posting_time="15:00:00",
        item_code="Milk Powder",
        warehouse="Stores - TC",
        qty=Decimal("-10"),
        rate=Decimal("0"),  # Computed by FIFO
        remarks="Customer dispatch: Milk Powder"
    ))

    return ledger, milk, milk_powder


def display_sle_table(sles: List[StockLedgerEntry], title: str):
    print_header(title)
    headers = [
        "Voucher", "Item", "Date", "Qty", "In Rate", "Out Rate", "Val Diff (₹)", "Bal Qty", "Bal Val (₹)", "FIFO Queue"
    ]
    col_widths = [12, 12, 10, 6, 8, 8, 12, 8, 11, 35]

    rows = []
    for s in sles:
        rows.append([
            s.voucher_no,
            s.item_code,
            s.posting_date,
            f"{float(s.actual_qty):+g}",
            f"₹{float(s.incoming_rate):g}" if s.incoming_rate > 0 else "-",
            f"₹{float(s.outgoing_rate):g}" if s.outgoing_rate > 0 else "-",
            f"₹{float(s.stock_value_difference):+,.2f}",
            f"{float(s.qty_after_transaction):g}",
            f"₹{float(s.stock_value):,.2f}",
            format_queue(s.stock_queue)
        ])
    print_table(headers, rows, col_widths)


def run_demo():
    print("\n" + "#" * 90)
    print("   ERPNEXT STOCK REPOSTING & VALUATION DEMO - MILK & MILK POWDER SCENARIO")
    print("#" * 90)

    # 1. Build initial ledger and run baseline
    ledger, milk, milk_powder = build_scenario_ledger()
    initial_sles = ledger.process_all()

    display_sle_table(initial_sles, "Baseline State: Before 10th Jan Rate Edit (10th Jan PR @ ₹60/L)")

    # 2. Simulate User Editing 10th Jan PR from ₹60 to ₹80
    print_header("User Action: Editing 10th January Purchase Receipt PR-001 (Rate: ₹60/L -> ₹80/L)")
    repost_engine = RepostEngine(ledger)
    result = repost_engine.simulate_rate_edit(
        voucher_no="PR-001",
        item_code="Milk",
        new_rate=Decimal("80.00")
    )

    # 3. Display updated SLE table
    display_sle_table(result["new_sles"], "Recalculated State: After Reposting (10th Jan PR @ ₹80/L)")

    # 4. Display exact diffs and impacted vouchers
    print_header("Detailed Impact Analysis & Comparison")
    diff_headers = ["Voucher", "Item", "Field Changed", "Baseline Value", "Reposted Value", "Impact Summary"]
    diff_widths = [10, 12, 18, 16, 16, 25]
    diff_rows = []

    for d in result["sle_diffs"]:
        v_no = d["voucher_no"]
        item = d["item_code"]

        if d["old_incoming_rate"] != d["new_incoming_rate"]:
            diff_rows.append([
                v_no, item, "Incoming Rate",
                f"₹{d['old_incoming_rate']:g}", f"₹{d['new_incoming_rate']:g}",
                f"+₹{d['new_incoming_rate'] - d['old_incoming_rate']:g}/unit"
            ])

        if d["old_outgoing_rate"] != d["new_outgoing_rate"]:
            diff_rows.append([
                v_no, item, "Outgoing Rate",
                f"₹{d['old_outgoing_rate']:g}", f"₹{d['new_outgoing_rate']:g}",
                f"+₹{d['new_outgoing_rate'] - d['old_outgoing_rate']:g}/unit"
            ])

        if d["delta_stock_value_diff"] != 0:
            diff_rows.append([
                v_no, item, "Valuation Diff",
                f"₹{d['old_stock_value_diff']:,.2f}", f"₹{d['new_stock_value_diff']:,.2f}",
                f"Delta: ₹{d['delta_stock_value_diff']:+,.2f}"
            ])

        if d["old_running_val"] != d["new_running_val"]:
            diff_rows.append([
                v_no, item, "Running Stock Val",
                f"₹{d['old_running_val']:,.2f}", f"₹{d['new_running_val']:,.2f}",
                f"Delta: ₹{d['new_running_val'] - d['old_running_val']:+,.2f}"
            ])

    print_table(diff_headers, diff_rows, diff_widths)

    # 5. Display GL Impact
    print_header("General Ledger (GL) Financial Reconciliations")
    gl_headers = ["Account", "Baseline Net (₹)", "Reposted Net (₹)", "Adjustment Required (₹)"]
    gl_widths = [32, 18, 18, 22]
    gl_rows = []
    for g in result["gl_diffs"]:
        gl_rows.append([
            g["account"],
            f"₹{g['old_net']:+,.2f}",
            f"₹{g['new_net']:+,.2f}",
            f"₹{g['adjustment_delta']:+,.2f}"
        ])
    print_table(gl_headers, gl_rows, gl_widths)

    print("\n" + "=" * 90)
    print("KEY TAKEAWAYS FOR ROHIT & THE HIRING TEAM:")
    print("1. 15th Jan Milk Delivery Note (DN-001): Outgoing rate remains ₹50/L (COGS unchanged!)")
    print("   because 80L was fully satisfied by the Opening Stock (100L @ ₹50). But running stock")
    print("   value and FIFO queue are updated.")
    print("2. 21st Jan Manufacture (MFG-001): Raw material cost increased by ₹1,000 (from ₹5,800 to ₹6,800).")
    print("   This dynamically updated Milk Powder incoming production rate from ₹580/Kg to ₹680/Kg.")
    print("3. 25th Jan Milk Powder Delivery Note (DN-002): COGS increased by ₹1,000 (from ₹5,800 to ₹6,800).")
    print("4. Total Stock In Hand on 25th Jan remains ₹1,200 (Milk 20L @ ₹60), because the +₹1,000 cost")
    print("   fully flowed through production into Milk Powder and was realized into customer COGS!")
    print("=" * 90 + "\n")


if __name__ == "__main__":
    run_demo()
