# Architecture & System Design: Stock Reposting Engine for ERPNext

## 1. System Overview

In an Enterprise Resource Planning (ERP) platform like ERPNext, inventory valuation determines not only stock asset values on the Balance Sheet (`Stock In Hand`), but also the direct profitability of sales on the Income Statement (`Cost of Goods Sold - COGS`).

When a transaction rate or quantity is altered retroactively, the system cannot simply update the single record in isolation. Because valuation follows sequential queue semantics (FIFO) or running weighted averages (Moving Average), **every subsequent consumption and conversion must be recalculated chronologically**.

This repository implements a production-grade, modular stock reposting architecture tailored for ERPNext.

---

## 2. Core Architectural Components

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Stock Reposting Engine                          │
└────────────────────────────────────────────────────────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
┌──────────────────┐      ┌──────────────────┐      ┌──────────────────┐
│  Dependency DAG  │      │ FIFO Queue Core  │      │  GL Reconciler   │
│  Resolver        │      │ Engine           │      │  (Perpetual Inv) │
└──────────────────┘      └──────────────────┘      └──────────────────┘
         │                         │                         │
         ▼                         ▼                         ▼
  Traverses BOM /           Evaluates layer-by-       Generates double-
  Manufacture graphs        layer consumption &       entry adjusting
  for cross-item costs      recomputes rates          GL entries
```

### A. FIFO Queue Core (`src/fifo_queue.py`)
- Represents discrete inventory batches as `[quantity, rate]`.
- Enforces strict positive invariants: prevents negative stock violations and invalid consumption.
- Handles partial consumption across arbitrary numbers of historical layers.
- Automatically merges consecutive layers sharing identical rates to minimize memory footprint and database serialization size.
- Uses Python `Decimal` with quantized rounding (`ROUND_HALF_UP`) to prevent floating-point drift.

### B. Stock Ledger & Forward Processor (`src/ledger.py`)
- Maintains chronological transaction logs.
- Emulates ERPNext's `tabStock Ledger Entry` schema.
- Orchestrates multi-item manufacturing transformations:
  $$\text{FG Incoming Rate} = \frac{\sum_{i=1}^n (\text{RM Qty}_i \times \text{RM Outgoing Rate}_i) + \text{Operating Costs}}{\text{FG Produced Qty}}$$
- Transfers value directly from consumed raw materials to produced finished goods.

### C. Dependency Graph Resolver (`src/repost_engine.py`)
- Identifies downstream items affected by upstream changes.
- If Item A is consumed to produce Item B, and Item B is consumed to produce Item C:
  $$\text{Item A (Raw)} \longrightarrow \text{Item B (WIP)} \longrightarrow \text{Item C (FG)}$$
- The DAG resolver performs a topological sort to guarantee that parents are recalculated before children.

### D. General Ledger Reconciler (`src/gl_mapper.py`)
- Models ERPNext's Perpetual Inventory accounting:
  - **Purchase Receipt:** Debit `Stock In Hand`, Credit `Stock Received But Not Billed`.
  - **Delivery Note:** Debit `Cost of Goods Sold (COGS)`, Credit `Stock In Hand`.
  - **Manufacturing Entry:** Credit `Stock In Hand (Raw Material)`, Debit `Stock In Hand (Finished Goods)`.
- Generates delta adjustment entries to balance general ledger accounts.

---

## 3. Concurrency Control and Locking Strategy

In high-throughput environments, multiple background workers or user actions can clash if modifying the same inventory partitions.

### The Challenge: Race Conditions During Live Transactions
Suppose the background repost worker is recalculating entries from January 10th for `Milk` in warehouse `Stores - TC`. If a sales dispatch is submitted right at that moment, it could read an intermediate or uncommitted FIFO queue state, leading to queue corruption.

### Solution: Fine-Grained Distributed Advisory Locks
We implement an advisory locking mechanism scoped specifically to the `(item_code, warehouse)` partition:

```python
def execute_repost_with_lock(item_code: str, warehouse: str, repost_fn):
    lock_key = f"lock:stock_repost:{item_code}:{warehouse}"
    
    # Acquire Redis distributed lock with timeout
    with redis_client.lock(lock_key, timeout=300, blocking_timeout=10):
        # 1. Fetch latest entries inside atomic transaction
        # 2. Recompute queues forward
        # 3. Commit batch SLE updates
        # 4. Enqueue downstream child items in DAG
        repost_fn()
```

- Scoped per item-warehouse pair so that unrelated warehouses/items are never blocked.
- Live checkout operations can wait briefly or be held in an ingestion queue until the lock releases.

---

## 4. Idempotency and Fault Recovery

To ensure production reliability:
1. **Idempotent Execution:** Rerunning the repost process over already-recalculated transactions produces zero net change.
2. **Transaction Atomicity:** Reposting updates are committed in database batches.
3. **Queue Checkpoints:** Periodic snapshots store `(qty, stock_value, serialized_queue)` allowing the engine to resume from the nearest valid checkpoint rather than recalculating from Genesis.
