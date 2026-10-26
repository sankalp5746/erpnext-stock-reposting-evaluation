# Technical Assessment: Stock Reposting and Valuation in ERPNext

**Candidate:** Meghraj  
**Evaluation Reviewer:** Rohit  
**Focus Area:** ERPNext Stock Valuation, FIFO Queue Management, Repost Item Valuation (RIV), and Accounting Ledger Reconciliation

---

## Executive Summary of the Scenario

- **Item 1:** Milk (Valuation Method: `FIFO`)
- **Item 2:** Milk Powder (Valuation Method: `FIFO`)
- **Initial Transaction Timeline:**
  1. *Opening Stock:* 100L Milk @ ₹50/L
  2. *10th January:* Milk Purchase Receipt of 50L @ ₹60/L (PR-001)
  3. *15th January:* Milk Delivery Note of 80L (DN-001)
  4. *20th January:* Milk Purchase Receipt of 50L @ ₹60/L (PR-002)
  5. *21st January:* Manufacture Entry: 100L Milk Consumed, 10 Kg Milk Powder Produced (MFG-001)
  6. *25th January:* Milk Powder Delivery Note of 10 Kg (DN-002)
- **User Action:** On a later date, the user amends/edits the **10th January Purchase Receipt**, changing the incoming rate from **₹60/L to ₹80/L**.

Below are the detailed, production-grade answers to all four questions posed in the prompt.

---

## Question 1: What transactions in Stock should be affected by this change?

When the 10th January Purchase Receipt incoming rate is increased from ₹60/L to ₹80/L (+₹20/L, total inward valuation delta of +₹1,000), the impact spans **both directly modified transactions, intermediate running balances, and downstream multi-level manufacturing & customer dispatch transactions**:

### 1. 10th January Purchase Receipt (PR-001) — [Directly Affected]
- **Actual Qty:** +50L
- **Incoming Rate:** Increases from ₹60.00/L to **₹80.00/L**
- **Stock Value Difference:** Increases from +₹3,000.00 to **+₹4,000.00** (Delta: **+₹1,000.00**)
- **Running Stock Value:** Increases from ₹8,000.00 to **₹9,000.00**
- **FIFO Queue:** Changes from `[[100, 50], [50, 60]]` to `[[100, 50], [50, 80]]`

### 2. 15th January Milk Delivery Note (DN-001) — [Partially Affected / Running Balance & Queue]
- **Actual Qty:** -80L
- **Outgoing Rate & COGS Impact:** **UNCHANGED at ₹50.00/L (Total COGS: ₹4,000.00)**.
  - *Why?* Under strict FIFO, the 80L outward dispatch is completely satisfied by the Opening Stock layer (100L @ ₹50.00). The 10th January batch (50L @ ₹80) has not yet been consumed.
- **Stock Value & Queue Impact:** **AFFECTED**.
  - The remaining 70L in stock now consists of 20L @ ₹50 (= ₹1,000) + 50L @ ₹80 (= ₹4,000).
  - Running Stock Value after transaction increases from ₹4,000.00 to **₹5,000.00** (Delta: **+₹1,000.00**).
  - Average Valuation Rate increases from ₹57.14/L to **₹71.43/L**.
  - FIFO Queue becomes `[[20, 50], [50, 80]]` (was `[[20, 50], [50, 60]]`).

### 3. 20th January Milk Purchase Receipt (PR-002) — [Running Balance & Queue Affected]
- **Actual Qty:** +50L @ ₹60.00/L
- **Incoming Rate:** Unchanged at ₹60.00/L. Stock Value Difference unchanged (+₹3,000.00).
- **Stock Value & Queue Impact:** **AFFECTED**.
  - Running Stock Value increases from ₹7,000.00 to **₹8,000.00** (Delta: **+₹1,000.00**).
  - FIFO Queue changes to `[[20, 50], [50, 80], [50, 60]]`. (Note: In the baseline state, the two ₹60 layers merged into `[100, 60]`; now they remain distinct buckets because rates differ).

### 4. 21st January Manufacture Entry (MFG-001) — [CRITICALLY AFFECTED: Raw Material & Finished Goods]
This is a multi-item transformation voucher where the raw material valuation directly dictates finished goods capitalization:
- **Part A: Raw Material Consumption (Milk, -100L):**
  - Consumed from FIFO Queue:
    - 20L @ ₹50.00 = ₹1,000.00
    - 50L @ **₹80.00** = **₹4,000.00** (was 50L @ ₹60.00 = ₹3,000.00; **Delta: +₹1,000.00**)
    - 30L @ ₹60.00 = ₹1,800.00
  - Total Raw Material Consumption Cost: Increases from ₹5,800.00 to **₹6,800.00** (Delta: **+₹1,000.00**).
  - Effective Outgoing Rate: Increases from ₹58.00/L to **₹68.00/L**.
  - Stock Value Difference: Changes from -₹5,800.00 to **-₹6,800.00**.
  - Remaining Milk in warehouse: 20L @ ₹60.00 = ₹1,200.00.
- **Part B: Finished Good Production (Milk Powder, +10 Kg):**
  - In ERPNext manufacturing, total raw material costs (plus operating costs) are absorbed into finished goods incoming rate:
    $$\text{Incoming Rate} = \frac{\text{Total Consumed Cost}}{\text{Produced Quantity}} = \frac{₹6,800.00}{10\text{ Kg}} = ₹680.00/\text{Kg}$$
  - Baseline Incoming Rate was ₹580.00/Kg. **New Incoming Rate is ₹680.00/Kg** (Delta: **+₹100.00/Kg**).
  - Capitalized Finished Good Value: Increases from ₹5,800.00 to **₹6,800.00**.

### 5. 25th January Milk Powder Delivery Note (DN-002) — [CRITICALLY AFFECTED: Downstream COGS]
- **Actual Qty:** -10 Kg Milk Powder
- **Outgoing Rate:** Increases from ₹580.00/Kg to **₹680.00/Kg**
- **Cost of Goods Sold (COGS):** Increases from ₹5,800.00 to **₹6,800.00** (Delta: **+₹1,000.00**)
- **Stock Value Difference:** Changes from -₹5,800.00 to **-₹6,800.00**.

### Summary Matrix of Affected Transactions

| Voucher No | Date | Item | Actual Qty | Old Rate | New Rate | Old Val Diff | New Val Diff | Net P&L / COGS Impact |
|:---|:---|:---|:---|:---|:---|:---|:---|:---|
| **PR-001** | 10-Jan | Milk | +50 L | ₹60.00 | **₹80.00** | +₹3,000 | **+₹4,000** | Balance Sheet (Inventory/Liability) |
| **DN-001** | 15-Jan | Milk | -80 L | ₹50.00 | ₹50.00 | -₹4,000 | -₹4,000 | **₹0.00 (COGS Unchanged)** |
| **PR-002** | 20-Jan | Milk | +50 L | ₹60.00 | ₹60.00 | +₹3,000 | +₹3,000 | Running Value +₹1,000 |
| **MFG-001 (RM)** | 21-Jan | Milk | -100 L | ₹58.00 | **₹68.00** | -₹5,800 | **-₹6,800** | Transferred to FG (+₹1,000) |
| **MFG-001 (FG)** | 21-Jan | Milk Powder | +10 Kg | ₹580.00 | **₹680.00** | +₹5,800 | **+₹6,800** | Capitalized Stock Value (+₹1,000) |
| **DN-002** | 25-Jan | Milk Powder | -10 Kg | ₹580.00 | **₹680.00** | -₹5,800 | **-₹6,800** | **+₹1,000 COGS Expense Increase** |

---

## Question 2: How should ERPNext recalculate the valuation of the subsequent transactions?

ERPNext manages this via its **Repost Item Valuation (RIV)** framework (`erpnext.stock.doctype.repost_item_valuation.repost_item_valuation`):

### 1. Triggering and Document Enqueuing
- When the user cancels and amends `PR-001`, ERPNext intercepts the submission.
- A `Repost Item Valuation` document is created in `Queued` state with:
  - `item_code`: "Milk"
  - `warehouse`: "Stores - TC"
  - `posting_date`: "2026-01-10"
  - `posting_time`: (time of PR-001)
  - `voucher_type`: "Purchase Receipt", `voucher_no`: "PR-001"

### 2. Dependency Discovery (Cross-Item Traversal)
- Milk is consumed on 21st January in `MFG-001` (Stock Entry - Manufacture) to produce **Milk Powder**.
- The reposting engine inspects downstream transactions and detects that the manufactured item `Milk Powder` has a cost dependency on `Milk`.
- Therefore, `Milk Powder` for warehouse `Stores - TC` from `2026-01-21` onwards is added to the recalculation queue.

### 3. Forward Chronological Simulation of FIFO Queues
For each `(item_code, warehouse)` pair, ERPNext:
1. Loads the last valid stock ledger state **immediately prior** to `2026-01-10` (here, after `OPENING-001` on Jan 01: `queue = [[100, 50]]`, `qty = 100`, `val = 5000`).
2. Fetches all subsequent Stock Ledger Entries (`tabStock Ledger Entry`) sorted strictly by `(posting_date, posting_time, creation)`.
3. Sequentially steps forward:
   - **Inward entries (+qty):** Pushes new `[qty, incoming_rate]` onto the tail of `stock_queue`. Updates `qty_after_transaction` and `stock_value`.
   - **Outward entries (-qty):** Dequeues stock from the head of `stock_queue`. Computes `stock_value_difference` as the exact sum of consumed layers, calculates `outgoing_rate = stock_value_difference / abs(actual_qty)`.
   - Updates the SLE record with recalculated `stock_value_difference`, `valuation_rate`, `stock_value`, and updated serialized `stock_queue`.

### 4. Manufacturing Valuation Transfer
- When `MFG-001` (Milk consumption) is reached, its recomputed consumed value (-₹6,800.00) is used to update the parent `Stock Entry` document's basic amount.
- The finished goods SLE for `Milk Powder` is updated with `incoming_rate = 6800 / 10 = ₹680.00/Kg`.
- The reposting engine proceeds to recalculate all downstream entries for `Milk Powder` (triggering recalculation of `DN-002`).

### 5. General Ledger (GL) Synchronization (Perpetual Inventory)
In an ERP with automated perpetual inventory:
- Old GL entries generated by the modified/subsequent vouchers are either cancelled/reversed or updated with delta adjustments.
- **Stock In Hand:** Adjusted for the new inventory valuations.
- **Stock Received But Not Billed:** Credited by an additional ₹1,000 for the revised supplier receipt liability.
- **Cost of Goods Sold (COGS):** Debited by an additional ₹1,000 on 25th January for `DN-002`.

---

## Question 3: How would you design the reposting logic to handle this change for FIFO?

A production-grade reposting engine must be **accurate, concurrent-safe, idempotent, and performant**. Below is the architectural design:

```
                      [ User Edits Past Voucher ]
                                   │
                                   ▼
                   [ Create Repost Item Valuation ]
                                   │
                                   ▼
                [ Build Dependency Graph (DAG) ]
                   │                         │
            (Direct Item: Milk)    (Manufactured Item: Milk Powder)
                   │                         │
                   └───────────┬─────────────┘
                               ▼
               [ Acquire Advisory Lock on (Item, WH) ]
                               │
                               ▼
            [ Fetch Last Known Valid Checkpoint ]
                               │
                               ▼
         [ Forward Chronological FIFO Queue Traversal ]
            ├── Match inward rates / push layers
            ├── Dequeue outward layers (compute COGS)
            └── Propagate RM consumption to FG production
                               │
                               ▼
            [ Atomic Batch Update of SLE Records ]
                               │
                               ▼
            [ Reconcile General Ledger (GL) Entries ]
                               │
                               ▼
                   [ Release Advisory Lock ]
```

### Key Design Pillars:

### 1. Directed Acyclic Graph (DAG) of Dependencies
Instead of recomputing the entire stock ledger across the entire database, construct a minimal subgraph of affected tuples:
$$\text{Affected Tuple} = (\text{Item Code}, \text{Warehouse}, \text{Timestamp } t_0)$$
- **Upstream $\to$ Downstream:** Track BOM consumption (`Stock Entry`, `Work Order`, `Subcontracting Receipt`).
- **Topological Sorting:** Process items in topological order: Raw Materials first, intermediate WIP sub-assemblies second, finished goods last.

### 2. Checkpointing and Fast Forward
- Maintain periodic balance snapshots (e.g., end-of-month or every $K$ entries) storing `(checkpoint_qty, checkpoint_value, checkpoint_fifo_queue)`.
- When an edit occurs at $t_0$, find the nearest checkpoint $t_{cp} \le t_0$, restore queue state, and only replay entries from $t_{cp}$ forward.

### 3. Distributed Concurrency Control (Advisory Locks)
- **The Problem:** If a user posts a live delivery note while a background job is reposting past entries for the same item/warehouse, race conditions will corrupt `stock_queue`.
- **Solution:** Acquire a fine-grained Redis or MariaDB advisory lock:
  ```python
  lock_key = f"stock_repost_lock:{item_code}:{warehouse}"
  with acquire_distributed_lock(lock_key, timeout=120):
      # Execute forward calculation safely
  ```
- Any live transactions attempting to post to this item/warehouse during the brief recalculation window will wait or queue transparently.

### 4. Idempotency and Non-Destructive GL Entries
- The recalculation engine must be pure and idempotent: running it multiple times on the same input produces the exact same state without side effects.
- For GL entries, rather than hard-deleting posted accounting entries (which breaks audit chains in strict GAAP/IFRS environments), post **Correction / Adjustment GL Entries** referencing the `Repost Item Valuation` document.

---

## Question 4: What problems could occur if the system stores a running balance in every Stock Ledger Entry?

Historically, ERPNext stored `qty_after_transaction`, `stock_value`, and `valuation_rate` directly in every `tabStock Ledger Entry` row. While this makes reading historical balances simple (`SELECT qty_after_transaction ... ORDER BY posting_date DESC LIMIT 1`), it introduces severe architectural pitfalls in high-volume enterprise environments:

### 1. Massive Write Amplification ($O(N)$ Cascading Updates)
- If an item has 150,000 stock ledger entries over 3 years, editing a single receipt from 2 years ago forces the database to rewrite **all subsequent 100,000+ rows**.
- Every row update generates database WAL (Write-Ahead Log) / InnoDB redo logs, binlogs for replication, and triggers database write bottlenecks.

### 2. High Lock Contention and Deadlocks (InnoDB Row Locks)
- In MySQL/MariaDB, executing:
  ```sql
  UPDATE `tabStock Ledger Entry`
  SET stock_value = stock_value + 1000
  WHERE item_code = 'Milk' AND posting_date >= '2026-01-10';
  ```
  places exclusive index range locks on thousands of rows.
- If concurrent operational transactions (POS checkout, warehouse scanner, purchase receipt) attempt to insert new SLEs for the same item, they will stall waiting for locks, resulting in **Error 1205: Lock wait timeout exceeded** or **Error 1213: Deadlock found when trying to get lock**.

### 3. State Drift and Incomplete Reposting Corruption
- If the background worker executing the cascading update crashes (server reboot, Out-Of-Memory killer, MariaDB timeout, process kill), the ledger is left partially updated.
- Entries from Jan 10 to Jan 18 might have new balances, while Jan 19 to Jan 25 still have old balances. This causes **silent ledger corruption** that is notoriously difficult to diagnose.

### 4. Decoupling of Stock Ledger and General Ledger (GL)
- When SLE running balances are rewritten retroactively, the corresponding `tabGL Entry` records for closed financial periods become out-of-sync with physical inventory value.
- Auditors will discover that the Balance Sheet's *Stock In Hand* account does not match the *Stock Balance* report for past audited quarters.

### 5. Violation of Audit Trail Immutability
- Financial and supply-chain regulatory standards (SOX, IFRS, US GAAP) require an immutable audit trail.
- Mutating historical rows in `tabStock Ledger Entry` destroys historical provenance: it becomes impossible to prove cryptographically or historically what the reported inventory valuation was on January 16th prior to the edit.

### Modern Architectural Remedies:
1. **Event Sourcing (Immutable Delta Ledger):** SLEs should store only deltas (`actual_qty`, `stock_value_difference`). Running balances are derived dynamically or cached in a separate read-optimized snapshot table.
2. **Snapshot / Checkpoint Tables:** Maintain periodic snapshots (`tabStock Balance Snapshot`) rather than updating every historical row.
3. **Adjustment Vouchers:** Instead of amending past documents retroactively, post forward-looking adjustment documents (e.g., *Landed Cost Voucher*, *Stock Reconciliation*, or *Debit Note*) that absorb rate differences into current/open periods.
