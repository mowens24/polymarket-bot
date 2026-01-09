"""Position limit tracking and enforcement."""

from __future__ import annotations

from typing import Dict, Optional

from config import (
    MAX_CONCURRENT_POSITIONS,
    MAX_DAILY_TRADES,
    MAX_POSITION_USD,
)
from logger import log_error, log_info


class PositionLimits:
    """Tracks active positions and enforces trading limits."""

    def __init__(self):
        self.active_positions: Dict[str, float] = {}  # market_id -> usd_amount
        self.daily_trade_count: int = 0
        self.total_exposure_usd: float = 0.0

    def can_trade(self, market_id: str, amount_usd: float) -> bool:
        """Check if trade respects all position limits."""
        # Check daily trade count
        if self.daily_trade_count >= MAX_DAILY_TRADES:
            log_error(
                f"Daily trade limit ({MAX_DAILY_TRADES}) reached - no more trades today"
            )
            return False

        # Check position size limit
        if amount_usd > MAX_POSITION_USD:
            log_error(
                f"Trade ${amount_usd:.2f} exceeds MAX_POSITION_USD ${MAX_POSITION_USD:.2f}"
            )
            return False

        # Check concurrent positions limit
        if (
            len(self.active_positions) >= MAX_CONCURRENT_POSITIONS
            and market_id not in self.active_positions
        ):
            log_error(
                f"Max concurrent positions ({MAX_CONCURRENT_POSITIONS}) reached"
            )
            return False

        # Check total exposure limit (estimate: 80% of max concurrent * max per position)
        max_exposure = MAX_CONCURRENT_POSITIONS * MAX_POSITION_USD * 0.8
        new_exposure = self.total_exposure_usd + amount_usd
        if new_exposure > max_exposure:
            log_error(
                f"Total exposure ${new_exposure:.2f} exceeds safe limit ${max_exposure:.2f}"
            )
            return False

        return True

    def add_position(self, market_id: str, amount_usd: float) -> None:
        """Record a new or increased position."""
        if market_id not in self.active_positions:
            self.active_positions[market_id] = 0.0
        self.active_positions[market_id] += amount_usd
        self.total_exposure_usd += amount_usd
        self.daily_trade_count += 1
        log_info(
            f"Position added: market={market_id}, amount=${amount_usd:.2f}, "
            f"total_exposure=${self.total_exposure_usd:.2f}"
        )

    def close_position(self, market_id: str, pnl_usd: Optional[float] = None) -> None:
        """Record a closed position."""
        if market_id in self.active_positions:
            amount = self.active_positions.pop(market_id)
            self.total_exposure_usd -= amount
            status = f"PnL: ${pnl_usd:.2f}" if pnl_usd is not None else "N/A"
            log_info(
                f"Position closed: market={market_id}, amount=${amount:.2f}, {status}, "
                f"remaining_exposure=${self.total_exposure_usd:.2f}"
            )

    def reset_daily_counters(self) -> None:
        """Reset daily trade count (call at start of each day)."""
        self.daily_trade_count = 0
        log_info("Daily trade counters reset")

    def get_status(self) -> dict:
        """Return current position status."""
        return {
            "active_positions": len(self.active_positions),
            "total_exposure_usd": self.total_exposure_usd,
            "daily_trades": self.daily_trade_count,
            "markets": list(self.active_positions.keys()),
        }
