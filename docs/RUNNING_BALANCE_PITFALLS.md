# Deep Dive: The Pitfalls of Storing Running Balances in Stock Ledger Entries

## Executive Summary

A common design pattern in traditional databases is denormalizing running totals—such as `qty_after_transaction`, `stock_value`, and `valuation_rate`—directly onto every ledger row. In ERP systems, this is known as the **Running Balance Ledger Pattern**.

While this allows instant $O(1)$ balance queries (`SELECT qty_after_transaction FROM tabStock Ledger Entry WHERE item_code = 'X' ORDER BY posting_date DESC, posting_time DESC LIMIT 1`), it incurs catastrophic operational costs when backdated transactions or retro-active rate amendments are permitted.

This document breaks down the technical reasons why storing mutable running balances in ledger rows degrades system performance and integrity, and presents modern architectural alternatives.

---

## 1. The $O(N)$ Write Amplification Problem

When all transactions are strictly append-only in real-time, storing a running balance costs only $O(1)$ per write:
$$\text{New Running Qty} = \text{Previous Running Qty} + \text{Actual Qty}$$

However, the moment a user **edits**, **cancels**, or **backdates** a transaction at index $k$ in an inventory history of $N$ transactions:
$$\text{Update Cost} = O(N - k) \text{ row rewrites}$$

```
Index:    1      2      3            k               N
Entry:  [SLE]──[SLE]──[SLE]──...──▶[SLE*]──▶[SLE]──▶[SLE]──▶[SLE]
                                     ▲        ▲       ▲       ▲
                           Rate Edited!       │       │       │
                                              └───────┴───────┴── MUST REWRITE ALL (N - k) ROWS!
```

### Real-World Enterprise Impact:
- An enterprise manufacturing facility generates 5,000 transactions/day.
- After 2 years, an item has over 3,000,000 ledger rows across 20 regional warehouses.
- An accountant edits a freight charge on a Purchase Receipt from 6 months ago ($k \approx 750,000$).
- The database is forced to update **2,250,000 rows**.
- Disk I/O spikes, buffer pools are flushed, replication lag soars, and the database engine throttles.

---

## 2. Lock Contention and Deadlocks (InnoDB / Relational Engines)

In relational databases (e.g. MariaDB / MySQL with InnoDB):
1. An `UPDATE` on a range of rows acquires exclusive index locks (`X locks`) and Next-Key / Gap locks to prevent phantom reads.
2. When the repost worker executes:
   ```sql
   UPDATE `tabStock Ledger Entry`
   SET stock_value = ...
   WHERE item_code = 'Milk' AND warehouse = 'Stores - TC'
     AND (posting_date > '2026-01-10' OR (posting_date = '2026-01-10' AND posting_time >= '10:00:00'))
   ```
   it holds row locks across thousands of records.
3. Simultaneously, an operator at the packing station is trying to submit a Delivery Note for `Milk`, which needs to insert a new row or lock the latest row.
4. **Result:**
   - **Error 1205 (HY000): Lock wait timeout exceeded; try restarting transaction**
   - **Error 1213 (40001): Deadlock found when trying to get lock; try restarting transaction**
5. Critical warehouse operations halt.

---

## 3. State Drift and Ledger Corruption Under Partial Failures

A multi-thousand row update is vulnerable to catastrophic mid-flight interruptions:
- Background worker killed by Linux OOM (Out Of Memory) killer.
- Database connection dropped or server restarted.
- Process timeout during execution.

If transaction atomicity is breached or updates are committed in non-atomic chunks, the ledger becomes **internally inconsistent**:
- Rows from Day 10 to Day 40 carry the new recalculated balance.
- Rows from Day 41 to Day 100 carry the old balance.
- Physical inventory reports, GL balances, and stock valuation completely decouple. Diagnosing this desynchronization requires expensive forensic recalculations.

---

## 4. Financial Audit and Regulatory Violations (SOX / GAAP / IFRS)

Strict financial standards enforce **Ledger Immutability**:
- A ledger should be a write-once, append-only log of economic events.
- If an auditor inspects the ledger for January 31st to close Q1 financials, and an engineer later runs an update that alters the `stock_value` column on January 15th's rows, the historical books have been mutated.
- The financial statement generated on February 1st no longer matches the database query run on March 1st.

---

## 5. Architectural Solutions & Best Practices

| Architecture | Read Performance | Write / Edit Cost | Audit Integrity | Concurrency |
|:---|:---|:---|:---|:---|
| **Mutable Running Balances** (Traditional) | $O(1)$ | $O(N)$ rewrite | Poor (historical rows mutated) | Severe lock contention |
| **Pure Event Sourcing** (Append-Only) | $O(N)$ without cache | $O(1)$ append | Perfect (immutable log) | Non-blocking writes |
| **Hybrid Snapshot Checkpointing** (Recommended) | $O(1)$ via checkpoint | $O(K)$ from checkpoint | High (adjustments posted as deltas) | Isolated by partition |

### Recommended Hybrid Design for ERPNext:
1. **Delta-Only Stock Ledger Entry:**
   Store only the transaction facts:
   `name`, `posting_datetime`, `item_code`, `warehouse`, `actual_qty`, `stock_value_difference`.
2. **Periodic Checkpoint Table (`tabStock Checkpoint`):**
   Record daily or weekly balance checkpoints:
   `item_code`, `warehouse`, `checkpoint_date`, `balance_qty`, `stock_value`, `fifo_queue_json`.
3. **Adjustment Vouchers for Retroactive Edits:**
   Instead of modifying past documents, post an explicit **Stock Valuation Adjustment Voucher** on the current date, carrying the valuation variance into the current open accounting period without altering closed historical records.
