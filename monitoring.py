"""Trade metrics and monitoring with alerts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List

from logger import log_error, log_info


class TradeMetrics:
    """Tracks trading performance metrics and detects anomalies."""

    def __init__(self, loss_limit_usd: float = 50.0, loss_streak_alert: int = 3):
        self.trades: List[Dict] = []
        self.loss_limit_usd = loss_limit_usd
        self.loss_streak_alert = loss_streak_alert
        self.daily_loss_usd = 0.0
        self.loss_streak = 0

    def record_trade(
        self,
        market_id: str,
        side: str,
        amount_usd: float,
        price: float,
        is_dry_run: bool = True,
    ) -> None:
        """Record a trade execution."""

        trade = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "market_id": market_id,
            "side": side,
            "amount_usd": amount_usd,
            "price": price,
            "is_dry_run": is_dry_run,
        }
        self.trades.append(trade)
        log_info(
            f"Trade recorded: {side.upper()} ${amount_usd:.2f} @ ${price:.4f} "
            f"(total trades: {len(self.trades)})"
        )

    def record_pnl(self, market_id: str, pnl_usd: float) -> None:
        """Record P&L for a closed trade and check for anomalies."""
        if pnl_usd < 0:
            self.daily_loss_usd += abs(pnl_usd)
            self.loss_streak += 1
            log_info(f"Loss recorded: ${pnl_usd:.2f}, daily loss: ${self.daily_loss_usd:.2f}")

            # Alert on loss limit breach
            if self.daily_loss_usd > self.loss_limit_usd:
                log_error(
                    f"DAILY LOSS LIMIT BREACH: ${self.daily_loss_usd:.2f} > "
                    f"${self.loss_limit_usd:.2f} - CONSIDER STOPPING"
                )

            # Alert on loss streak
            if self.loss_streak >= self.loss_streak_alert:
                log_error(
                    f"LOSS STREAK ALERT: {self.loss_streak} consecutive losses - "
                    "review strategy or stop trading"
                )
        else:
            self.loss_streak = 0
            log_info(f"Win recorded: ${pnl_usd:.2f}")

    def get_statistics(self) -> Dict:
        """Return trading statistics."""
        if not self.trades:
            return {"trades": 0}

        return {
            "total_trades": len(self.trades),
            "dry_run_trades": sum(1 for t in self.trades if t["is_dry_run"]),
            "live_trades": sum(1 for t in self.trades if not t["is_dry_run"]),
            "daily_loss_usd": self.daily_loss_usd,
            "current_loss_streak": self.loss_streak,
        }

    def reset_daily_stats(self) -> None:
        """Reset daily metrics (call at start of each day)."""
        self.daily_loss_usd = 0.0
        self.loss_streak = 0
        log_info("Daily metrics reset")

    def print_summary(self) -> None:
        """Print trading metrics summary."""
        stats = self.get_statistics()
        log_info(
            f"Metrics: {stats['total_trades']} total, "
            f"{stats['live_trades']} live, "
            f"Daily loss: ${stats['daily_loss_usd']:.2f}"
        )
