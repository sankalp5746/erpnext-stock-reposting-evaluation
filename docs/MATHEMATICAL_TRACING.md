# Mathematical Tracing & Ledger Ledger Diffs

This document presents the exact transaction-by-transaction mathematical walkthrough for the Milk and Milk Powder scenario, comparing the baseline state (10th Jan PR @ ₹60/L) against the recalculated state (10th Jan PR @ ₹80/L).

---

## 1. Baseline State (Before Rate Edit: PR-001 @ ₹60.00/L)

### Transaction 1: Opening Stock (2026-01-01)
- **Voucher:** Stock Entry - Opening (`OPENING-001`)
- **Item:** Milk | **Warehouse:** Stores - TC
- **Quantity:** +100 L | **Rate:** ₹50.00 / L
- **Calculation:**
  $$\text{Stock Value Difference} = 100 \times 50.00 = +₹5,000.00$$
  $$\text{Running Quantity} = 100\text{ L}, \quad \text{Running Stock Value} = ₹5,000.00$$
- **FIFO Queue:** `[[100, 50.00]]`
- **Accounting:** Debit Stock In Hand ₹5,000 | Credit Stock Adjustment ₹5,000

---

### Transaction 2: Milk Purchase Receipt (2026-01-10)
- **Voucher:** Purchase Receipt (`PR-001`)
- **Item:** Milk | **Warehouse:** Stores - TC
- **Quantity:** +50 L | **Incoming Rate:** ₹60.00 / L
- **Calculation:**
  $$\text{Stock Value Difference} = 50 \times 60.00 = +₹3,000.00$$
  $$\text{Running Quantity} = 100 + 50 = 150\text{ L}$$
  $$\text{Running Stock Value} = 5,000 + 3,000 = ₹8,000.00$$
- **FIFO Queue:** `[[100, 50.00], [50, 60.00]]`
- **Accounting:** Debit Stock In Hand ₹3,000 | Credit Stock Received But Not Billed ₹3,000

---

### Transaction 3: Milk Delivery Note (2026-01-15)
- **Voucher:** Delivery Note (`DN-001`)
- **Item:** Milk | **Warehouse:** Stores - TC
- **Quantity:** -80 L (Outward Customer Dispatch)
- **FIFO Consumption:**
  - Consume 80 L from Head Bucket: `[100, 50.00]`
  - Consumed Value: $80 \times 50.00 = ₹4,000.00$
  - Head bucket remaining: $100 - 80 = 20\text{ L @ ₹50.00}$
- **Calculation:**
  $$\text{Stock Value Difference} = -₹4,000.00$$
  $$\text{Outgoing Rate} = \frac{4,000}{80} = ₹50.00/\text{L}$$
  $$\text{Running Quantity} = 150 - 80 = 70\text{ L}$$
  $$\text{Running Stock Value} = 8,000 - 4,000 = ₹4,000.00$$
- **FIFO Queue:** `[[20, 50.00], [50, 60.00]]`
- **Accounting:** Debit Cost of Goods Sold (COGS) ₹4,000 | Credit Stock In Hand ₹4,000

---

### Transaction 4: Milk Purchase Receipt (2026-01-20)
- **Voucher:** Purchase Receipt (`PR-002`)
- **Item:** Milk | **Warehouse:** Stores - TC
- **Quantity:** +50 L | **Incoming Rate:** ₹60.00 / L
- **Calculation:**
  $$\text{Stock Value Difference} = 50 \times 60.00 = +₹3,000.00$$
  $$\text{Running Quantity} = 70 + 50 = 120\text{ L}$$
  $$\text{Running Stock Value} = 4,000 + 3,000 = ₹7,000.00$$
- **FIFO Queue:** `[[20, 50.00], [100, 60.00]]` *(Tail merged: 50 + 50 @ ₹60)*
- **Accounting:** Debit Stock In Hand ₹3,000 | Credit Stock Received But Not Billed ₹3,000

---

### Transaction 5: Manufacture Entry (2026-01-21)
- **Voucher:** Stock Entry - Manufacture (`MFG-001`)
- **Part A: Raw Material Consumption (Milk, -100 L)**
  - Consume 100 L across FIFO Queue:
    1. Bucket 1 (`[20, 50.00]`): Consume 20 L @ ₹50.00 = ₹1,000.00 (Bucket exhausted)
    2. Bucket 2 (`[100, 60.00]`): Consume 80 L @ ₹60.00 = ₹4,800.00 (20 L remaining)
  - Total Raw Material Consumed Cost:
    $$\text{Total RM Cost} = 1,000.00 + 4,800.00 = ₹5,800.00$$
  - Outgoing Rate: $5,800 / 100 = ₹58.00/\text{L}$
  - Stock Value Difference: $-₹5,800.00$
  - Running Milk Qty: $120 - 100 = 20\text{ L}$
  - Running Milk Value: $7,000 - 5,800 = ₹1,200.00$
  - Milk FIFO Queue: `[[20, 60.00]]`
- **Part B: Finished Good Production (Milk Powder, +10 Kg)**
  - Produced Qty: 10 Kg
  - Total Capitalized Value: ₹5,800.00
  - Incoming Rate:
    $$\text{Incoming Rate} = \frac{₹5,800.00}{10\text{ Kg}} = ₹580.00/\text{Kg}$$
  - Stock Value Difference: $+₹5,800.00$
  - Running Milk Powder Qty: $10\text{ Kg}$
  - Running Milk Powder Value: $₹5,800.00$
  - Milk Powder FIFO Queue: `[[10, 580.00]]`
- **Accounting:** Credit Stock In Hand (Milk) ₹5,800 | Debit Stock In Hand (Milk Powder) ₹5,800

---

### Transaction 6: Milk Powder Delivery Note (2026-01-25)
- **Voucher:** Delivery Note (`DN-002`)
- **Item:** Milk Powder | **Warehouse:** Stores - TC
- **Quantity:** -10 Kg
- **FIFO Consumption:** 10 Kg @ ₹580.00 / Kg = ₹5,800.00
- **Calculation:**
  $$\text{Stock Value Difference} = -₹5,800.00$$
  $$\text{Outgoing Rate} = ₹580.00/\text{Kg}$$
  $$\text{Running Quantity} = 0\text{ Kg}, \quad \text{Running Stock Value} = ₹0.00$$
- **FIFO Queue:** `[]`
- **Accounting:** Debit Cost of Goods Sold (COGS) ₹5,800 | Credit Stock In Hand ₹5,800

---

## 2. Recalculated State (After User Changes PR-001 Rate to ₹80.00/L)

### Transaction 1: Opening Stock (2026-01-01) — [Unchanged]
- **Milk FIFO Queue:** `[[100, 50.00]]` | **Running Val:** ₹5,000.00

---

### Transaction 2: Milk Purchase Receipt (2026-01-10) — [EDITED]
- **Rate:** Changed from ₹60.00 to **₹80.00 / L**
- **Calculation:**
  $$\text{Stock Value Difference} = 50 \times 80.00 = \mathbf{+₹4,000.00} \quad (\Delta +₹1,000.00)$$
  $$\text{Running Stock Value} = 5,000 + 4,000 = \mathbf{₹9,000.00} \quad (\text{was } ₹8,000.00)$$
- **FIFO Queue:** `[[100, 50.00], [50, 80.00]]`
- **Accounting Adjustment:** Debit Stock In Hand +₹1,000 | Credit Stock Received But Not Billed +₹1,000

---

### Transaction 3: Milk Delivery Note (2026-01-15) — [REPOSTED]
- **Quantity:** -80 L
- **FIFO Consumption:**
  - Consume 80 L from Opening Stock Bucket `[100, 50.00]`
  - Consumed Value: $80 \times 50.00 = ₹4,000.00$
  - Head bucket remaining: $20\text{ L @ ₹50.00}$
- **Key Observation:** **Outgoing Rate is STILL ₹50.00/L, COGS is STILL ₹4,000.00!**
- **Running Value:**
  $$\text{Running Stock Value} = 9,000 - 4,000 = \mathbf{₹5,000.00} \quad (\text{was } ₹4,000.00)$$
- **Valuation Rate:** $₹5,000 / 70 = ₹71.4286/\text{L}$ (was ₹57.1429/L)
- **FIFO Queue:** `[[20, 50.00], [50, 80.00]]`

---

### Transaction 4: Milk Purchase Receipt (2026-01-20) — [REPOSTED]
- **Quantity:** +50 L @ ₹60.00 / L (Inward value +₹3,000.00)
- **Running Value:**
  $$\text{Running Stock Value} = 5,000 + 3,000 = \mathbf{₹8,000.00} \quad (\text{was } ₹7,000.00)$$
- **FIFO Queue:** `[[20, 50.00], [50, 80.00], [50, 60.00]]`
  *(Note: Now there are 3 distinct buckets because rates 80 and 60 do not merge)*

---

### Transaction 5: Manufacture Entry (2026-01-21) — [CASCADED]
- **Part A: Raw Material Consumption (Milk, -100 L)**
  - Consume 100 L across FIFO Queue:
    1. Bucket 1 (`[20, 50.00]`): Consume 20 L @ ₹50.00 = ₹1,000.00 (Exhausted)
    2. Bucket 2 (`[50, 80.00]`): Consume 50 L @ **₹80.00** = **₹4,000.00** (was 50 @ ₹60 = ₹3,000; $\Delta +₹1,000$)
    3. Bucket 3 (`[50, 60.00]`): Consume 30 L @ ₹60.00 = ₹1,800.00 (20 L remaining)
  - Total Raw Material Consumed Cost:
    $$\text{Total RM Cost} = 1,000.00 + 4,000.00 + 1,800.00 = \mathbf{₹6,800.00} \quad (\Delta +₹1,000.00)$$
  - Effective Outgoing Rate: $6,800 / 100 = \mathbf{₹68.00/\text{L}}$ (was ₹58.00/L)
  - Stock Value Difference: $\mathbf{-₹6,800.00}$
  - Running Milk Value: $8,000 - 6,800 = \mathbf{₹1,200.00}$ (20 L @ ₹60)
  - Milk FIFO Queue: `[[20, 60.00]]`
- **Part B: Finished Good Production (Milk Powder, +10 Kg)**
  - Produced Qty: 10 Kg
  - Transferred Production Cost: **₹6,800.00**
  - New Incoming Rate:
    $$\text{Incoming Rate} = \frac{₹6,800.00}{10\text{ Kg}} = \mathbf{₹680.00/\text{Kg}} \quad (\text{was } ₹580.00/\text{Kg}, \Delta +₹100/\text{Kg})$$
  - Capitalized Finished Good Value: $\mathbf{₹6,800.00}$
  - Milk Powder FIFO Queue: `[[10, 680.00]]`

---

### Transaction 6: Milk Powder Delivery Note (2026-01-25) — [REPOSTED]
- **Quantity:** -10 Kg
- **FIFO Consumption:** 10 Kg @ **₹680.00 / Kg** = **₹6,800.00**
- **Calculation:**
  $$\text{Stock Value Difference} = \mathbf{-₹6,800.00} \quad (\text{was } -₹5,800.00)$$
  $$\text{Cost of Goods Sold (COGS)} = \mathbf{₹6,800.00} \quad (\Delta +₹1,000.00)$$
  $$\text{Running Quantity} = 0\text{ Kg}, \quad \text{Running Stock Value} = ₹0.00$$

---

## 3. Side-by-Side Comparison Matrix

| Step | Date | Voucher | Item | Actual Qty | Baseline Val Diff | Reposted Val Diff | Delta Diff | Outgoing Rate Baseline | Outgoing Rate Reposted |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 1 | 01-Jan | OPENING-001 | Milk | +100 | +₹5,000.00 | +₹5,000.00 | ₹0.00 | - | - |
| 2 | 10-Jan | PR-001 | Milk | +50 | +₹3,000.00 | **+₹4,000.00** | **+₹1,000.00** | - | - |
| 3 | 15-Jan | DN-001 | Milk | -80 | -₹4,000.00 | -₹4,000.00 | **₹0.00** | ₹50.00 | **₹50.00** |
| 4 | 20-Jan | PR-002 | Milk | +50 | +₹3,000.00 | +₹3,000.00 | ₹0.00 | - | - |
| 5a| 21-Jan | MFG-001 | Milk | -100 | -₹5,800.00 | **-₹6,800.00** | **-₹1,000.00** | ₹58.00 | **₹68.00** |
| 5b| 21-Jan | MFG-001 | Milk Powder | +10 | +₹5,800.00 | **+₹6,800.00** | **+₹1,000.00** | - | - |
| 6 | 25-Jan | DN-002 | Milk Powder | -10 | -₹5,800.00 | **-₹6,800.00** | **-₹1,000.00** | ₹580.00 | **₹680.00** |

---

## 4. General Ledger Reconciliation & Final Balance Sheet Impact

```
Baseline GL Net Balances (Before Edit):
-------------------------------------------------------------
Account                              Debit (₹)     Credit (₹)      Net (₹)
Cost of Goods Sold - TC               9,800.00           0.00    +9,800.00  (4,000 DN-001 + 5,800 DN-002)
Stock In Hand - TC                    1,200.00           0.00    +1,200.00  (20L Milk @ ₹60)
Stock Received But Not Billed - TC        0.00       6,000.00    -6,000.00  (3,000 PR-001 + 3,000 PR-002)
Stock Adjustment - TC                     0.00       5,000.00    -5,000.00  (Opening Offset)
-------------------------------------------------------------
Trial Balance Sum                     11,000.00      11,000.00        0.00 (Balanced!)

Reposted GL Net Balances (After Edit):
-------------------------------------------------------------
Account                              Debit (₹)     Credit (₹)      Net (₹)
Cost of Goods Sold - TC              10,800.00           0.00   +10,800.00  (+₹1,000.00 COGS!)
Stock In Hand - TC                    1,200.00           0.00    +1,200.00  (Unchanged: 20L Milk @ ₹60)
Stock Received But Not Billed - TC        0.00       7,000.00    -7,000.00  (+₹1,000.00 Liability)
Stock Adjustment - TC                     0.00       5,000.00    -5,000.00  (Unchanged)
-------------------------------------------------------------
Trial Balance Sum                     12,000.00      12,000.00        0.00 (Balanced!)
```
