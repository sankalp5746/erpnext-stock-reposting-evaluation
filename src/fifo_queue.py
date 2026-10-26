"""
FIFO Queue implementation for ERPNext Stock Valuation.
Handles bucket management, partial consumption, and valuation calculation.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List, Tuple, Optional
import copy


def quantize_currency(value: Decimal) -> Decimal:
    """Rounds to 2 decimal places for financial reporting."""
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def quantize_rate(value: Decimal) -> Decimal:
    """Rounds to 4 decimal places for unit valuation rates."""
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


def quantize_qty(value: Decimal) -> Decimal:
    """Rounds to 4 decimal places for stock quantities."""
    return value.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)


class FIFOQueue:
    """
    Manages a First-In-First-Out (FIFO) queue of stock batches.
    Each bucket is [qty, rate].
    """

    def __init__(self, queue: Optional[List[List[Decimal]]] = None):
        # Internal storage: List of [Decimal(qty), Decimal(rate)]
        self.queue: List[List[Decimal]] = []
        if queue:
            for item in queue:
                self.queue.append([Decimal(str(item[0])), Decimal(str(item[1]))])

    def add(self, qty: Decimal, rate: Decimal) -> None:
        """
        Adds incoming stock batch to the tail of the queue.
        Merges with tail if incoming rate matches tail's rate to keep queue compact.
        """
        qty = Decimal(str(qty))
        rate = Decimal(str(rate))
        if qty <= Decimal("0"):
            raise ValueError(f"Incoming quantity must be positive, got {qty}")

        if self.queue and self.queue[-1][1] == rate:
            self.queue[-1][0] += qty
        else:
            self.queue.append([qty, rate])

    def consume(self, qty: Decimal) -> Tuple[Decimal, List[Tuple[Decimal, Decimal, Decimal]]]:
        """
        Consumes outgoing stock from the head of the queue.
        Returns:
            Tuple of (total_consumed_value, list of (consumed_qty, rate, bucket_value))
        """
        qty = Decimal(str(qty))
        if qty <= Decimal("0"):
            raise ValueError(f"Consumption quantity must be positive, got {qty}")

        total_available = self.get_total_qty()
        if qty > total_available:
            raise ValueError(
                f"Negative stock violation! Requested to consume {qty}, but only {total_available} available."
            )

        consumed_breakdown: List[Tuple[Decimal, Decimal, Decimal]] = []
        remaining_to_consume = qty
        total_value = Decimal("0")

        while remaining_to_consume > Decimal("0") and self.queue:
            bucket_qty, bucket_rate = self.queue[0]

            if bucket_qty <= remaining_to_consume:
                # Consume entire bucket
                consumed_qty = bucket_qty
                bucket_val = consumed_qty * bucket_rate
                total_value += bucket_val
                consumed_breakdown.append((consumed_qty, bucket_rate, bucket_val))
                remaining_to_consume -= consumed_qty
                self.queue.pop(0)
            else:
                # Partially consume bucket
                consumed_qty = remaining_to_consume
                bucket_val = consumed_qty * bucket_rate
                total_value += bucket_val
                consumed_breakdown.append((consumed_qty, bucket_rate, bucket_val))
                self.queue[0][0] -= consumed_qty
                remaining_to_consume = Decimal("0")

        return total_value, consumed_breakdown

    def get_total_qty(self) -> Decimal:
        """Returns sum of all available quantities across all buckets."""
        return sum((b[0] for b in self.queue), Decimal("0"))

    def get_total_value(self) -> Decimal:
        """Returns total valuation of stock currently in the queue."""
        return sum((b[0] * b[1] for b in self.queue), Decimal("0"))

    def get_valuation_rate(self) -> Decimal:
        """Weighted average valuation rate across current stock in queue."""
        total_qty = self.get_total_qty()
        if total_qty == Decimal("0"):
            return Decimal("0")
        return self.get_total_value() / total_qty

    def clone(self) -> "FIFOQueue":
        """Returns a deep copy of the current queue."""
        return FIFOQueue(copy.deepcopy(self.queue))

    def to_list(self) -> List[List[Decimal]]:
        """Returns internal queue representation."""
        return [[b[0], b[1]] for b in self.queue]

    def __repr__(self) -> str:
        items_str = ", ".join(f"[{b[0]} @ ₹{b[1]}]" for b in self.queue)
        return f"FIFOQueue({items_str})"
