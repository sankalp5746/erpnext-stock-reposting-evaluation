# ERPNext Stock Reposting and Valuation Engine

[![Tests](https://img.shields.io/badge/tests-passing-brightgreen)](#running-the-test-suite)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-purple)](#)

A production-grade Python simulation, mathematical verification, and architectural design solving the **ERPNext Stock Reposting and Valuation Challenge** (FIFO Valuation with Multi-Level Manufacturing & Downstream Cascading).

---

## 📌 Problem Scenario

In **ERPNext**, two items (**Milk** and **Milk Powder**) both use the **FIFO** valuation method:

- **Opening stock for Milk:** 100L @ ₹50/L (01-Jan)
- **10th January:** Milk Purchase Receipt of 50L @ ₹60/L (`PR-001`)
- **15th January:** Milk Delivery Note of 80L (`DN-001`)
- **20th January:** Milk Purchase Receipt of 50L @ ₹60/L (`PR-002`)
- **21st January:** Manufacture Entry: 100L Milk Consumed $\to$ 10 Kg Milk Powder Produced (`MFG-001`)
- **25th January:** Milk Powder Delivery Note of 10 Kg (`DN-002`)

### ⚡ The Change:
> **The user edits the 10th January Purchase Receipt (`PR-001`) and changes the incoming rate from ₹60/L to ₹80/L.**

---

## 🚀 Quickstart: Run Demo & Tests

This repository is **zero-dependency** (pure standard Python library with `unittest` and `decimal`).

### 1. Run the Interactive Simulation & Comparison Table
```bash
python -m src.demo
```
*Outputs side-by-side transaction ledgers, FIFO queue buckets, valuation differences, and General Ledger (GL) reconciliations.*

### 2. Run the Full Test Suite
```bash
python run_tests.py
```
*Runs all 11 unit tests covering edge cases, negative stock guards, multi-level BOMs, and mathematical invariants in < 0.01s.*

---

## 📊 Summary of Impact: Before vs After Reposting

| Voucher | Date | Item | Qty | Rate (Before) | Rate (After) | Val Diff (Before) | Val Diff (After) | COGS / Financial Impact |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **PR-001** | 10-Jan | Milk | +50 L | ₹60.00 | **₹80.00** | +₹3,000.00 | **+₹4,000.00** | +₹1,000 Inward Asset / Liability |
| **DN-001** | 15-Jan | Milk | -80 L | ₹50.00 | **₹50.00** | -₹4,000.00 | -₹4,000.00 | **₹0.00 (COGS Unchanged! Satisfied by Opening Stock)** |
| **PR-002** | 20-Jan | Milk | +50 L | ₹60.00 | ₹60.00 | +₹3,000.00 | +₹3,000.00 | Running Stock Value +₹1,000 |
| **MFG-001 (RM)** | 21-Jan | Milk | -100 L | ₹58.00 | **₹68.00** | -₹5,800.00 | **-₹6,800.00** | Consumed RM cost increased by +₹1,000 |
| **MFG-001 (FG)** | 21-Jan | Milk Powder | +10 Kg | ₹580.00 | **₹680.00** | +₹5,800.00 | **+₹6,800.00** | Produced FG capitalization increased by +₹100/Kg |
| **DN-002** | 25-Jan | Milk Powder | -10 Kg | ₹580.00 | **₹680.00** | -₹5,800.00 | **-₹6,800.00** | **+₹1,000 COGS Expense Increase (Customer P&L)** |

---

## 💡 Answers to the 4 Core Technical Questions

### 1. What transactions in Stock should be affected by this change?
1. **10th Jan PR (`PR-001`):** Inward rate increases to ₹80/L; stock value difference increases by +₹1,000.
2. **15th Jan Milk DN (`DN-001`):** Outgoing rate and COGS are **completely unaffected** (remains ₹50/L) because 80L is consumed from Opening Stock. However, its running stock balance and subsequent FIFO queue are updated.
3. **20th Jan Milk PR (`PR-002`):** Incoming rate unchanged, but running stock value increases by +₹1,000.
4. **21st Jan Manufacture (`MFG-001`):**
   - **Milk Consumed:** Consumed cost rises from ₹5,800 to ₹6,800 (outgoing rate ₹58 $\to$ ₹68/L).
   - **Milk Powder Produced:** Production cost rises from ₹5,800 to ₹6,800 (incoming rate ₹580 $\to$ ₹680/Kg).
5. **25th Jan Milk Powder DN (`DN-002`):** Outgoing rate rises from ₹580 to ₹680/Kg; COGS increases by **+₹1,000**.
*(See [docs/QUESTIONS_ANSWERED.md](docs/QUESTIONS_ANSWERED.md) for full breakdown).*

### 2. How should ERPNext recalculate the valuation of subsequent transactions?
ERPNext triggers an asynchronous **`Repost Item Valuation` (RIV)** document:
1. Traverses the item dependency DAG across BOMs/Stock Entries (Milk $\to$ Milk Powder).
2. Re-evaluates all Stock Ledger Entries (`tabStock Ledger Entry`) from the earliest affected timestamp (Jan 10) in forward chronological order.
3. Rebuilds the FIFO queue `[[qty, rate], ...]` layer-by-layer: pushing inward receipts, popping outward dispatches, and computing raw material transfer costs into finished goods.
4. Synchronizes General Ledger entries (`tabGL Entry`) by posting adjustment deltas to *Stock In Hand*, *Stock Received But Not Billed*, and *Cost of Goods Sold*.

### 3. How would you design the reposting logic to handle this change for FIFO?
- **Dependency DAG:** Discover cross-item relationships dynamically and topologically sort items so upstream raw materials are reposted before downstream finished goods.
- **Distributed Advisory Locking:** Lock per `(item_code, warehouse)` partition in Redis/MariaDB to prevent live transactions from racing with background recalculation.
- **Queue Checkpoints:** Store periodic queue snapshots so the engine replays from the nearest checkpoint rather than table inception.
- **Idempotency & Reversal Entries:** Ensure recalculation can safely re-run without side-effects, generating balancing ledger corrections.
*(See [docs/DESIGN_AND_ARCHITECTURE.md](docs/DESIGN_AND_ARCHITECTURE.md) for details).*

### 4. What problems could occur if the system stores a running balance in every Stock Ledger Entry?
- **$O(N)$ Write Amplification:** Backdating an entry forces thousands of subsequent rows to be locked and updated.
- **Database Deadlocks & Lock Contention:** Exclusive row locks in InnoDB block concurrent checkouts, causing MySQL Errors 1205 and 1213.
- **State Drift / Silent Corruption:** Mid-flight worker crashes leave the ledger half-recalculated with corrupted running totals.
- **Audit Violations:** Mutating historical ledger rows violates GAAP/IFRS/SOX append-only compliance.
*(See [docs/RUNNING_BALANCE_PITFALLS.md](docs/RUNNING_BALANCE_PITFALLS.md) for details).*

---

## 📁 Repository Structure

```
erpnext-stock-reposting-valuation/
├── README.md                           # Overview, quickstart, and hiring assessment summary
├── run_tests.py                        # Zero-dependency test runner
├── docs/
│   ├── QUESTIONS_ANSWERED.md           # Exhaustive answers to the 4 assessment questions
│   ├── MATHEMATICAL_TRACING.md         # Step-by-step transaction walkthrough & queue tables
│   ├── DESIGN_AND_ARCHITECTURE.md      # Proposed reposting engine design, DAG, and locking
│   └── RUNNING_BALANCE_PITFALLS.md     # In-depth analysis of running balance issues in SLE
├── src/
│   ├── __init__.py
│   ├── models.py                       # Item, StockTransaction, StockLedgerEntry, GLEntry
│   ├── fifo_queue.py                   # Pure, robust FIFO queue engine with decimal precision
│   ├── ledger.py                       # Chronological StockLedger with manufacturing transfers
│   ├── repost_engine.py                # DAG dependency resolution and reposting manager
│   ├── gl_mapper.py                    # Perpetual Inventory GL entry generator
│   └── demo.py                         # Interactive CLI demonstration
└── tests/
    ├── __init__.py
    ├── test_milk_scenario.py           # Verifies the exact scenario from Rohit's prompt
    ├── test_fifo_queue.py              # FIFO queue edge cases, negative stock guards, splits
    ├── test_multi_level_bom.py         # Multi-tier BOM cascading (Raw Milk -> Cream -> Butter)
    └── test_reposting_engine.py        # Rate decreases, idempotency, and DAG detection
```

---

## 🧪 Test Coverage & Validation

All tests execute in milliseconds using Python's built-in `unittest`:

```bash
$ python run_tests.py
test_clone_independence (test_fifo_queue.TestFIFOQueue.test_clone_independence) ... ok
test_merges_consecutive_identical_rates (test_fifo_queue.TestFIFOQueue.test_merges_consecutive_identical_rates) ... ok
test_multi_batch_consumption (test_fifo_queue.TestFIFOQueue.test_multi_batch_consumption) ... ok
test_negative_stock_exception (test_fifo_queue.TestFIFOQueue.test_negative_stock_exception) ... ok
test_single_batch_add_and_consume (test_fifo_queue.TestFIFOQueue.test_single_batch_add_and_consume) ... ok
test_baseline_valuation_before_edit (test_milk_scenario.TestMilkScenario.test_baseline_valuation_before_edit) ... ok
test_reposting_after_rate_change_from_60_to_80 (test_milk_scenario.TestMilkScenario.test_reposting_after_rate_change_from_60_to_80) ... ok
test_three_tier_manufacturing_cascade (test_multi_level_bom.TestMultiLevelBOM.test_three_tier_manufacturing_cascade) ... ok
test_dependency_graph_detection (test_reposting_engine.TestRepostingEngine.test_dependency_graph_detection) ... ok
test_rate_decrease_reposting (test_reposting_engine.TestRepostingEngine.test_rate_decrease_reposting) ... ok
test_reposting_idempotency (test_reposting_engine.TestRepostingEngine.test_reposting_idempotency) ... ok

----------------------------------------------------------------------
Ran 11 tests in 0.002s

OK
```

---

## 👨‍💻 Candidate Note for Rohit

This solution is designed specifically to demonstrate **deep architectural fluency in Frappe & ERPNext's stock valuation internals**, accounting precision, and systems design under high transaction volume.

I look forward to discussing how these design principles can enhance ERPNext's performance and inventory integrity.
