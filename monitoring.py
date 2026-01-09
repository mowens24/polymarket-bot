"""Trade metrics and monitoring with alerts."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List

from logger import log_error, log_info


class PositionMonitor:
    """Track live P&L on open paper positions in real-time."""

    def __init__(self) -> None:
        self.positions: Dict[str, Dict[str, Any]] = {}  # market_id -> position data
        self.closed_positions: List[Dict[str, Any]] = []
        self.lock = Lock()

    def open_position(
        self, market_id: str, side: str, shares: float, entry_price: float
    ) -> None:
        """Record a new paper trade entry."""
        with self.lock:
            self.positions[market_id] = {
                "side": side,
                "shares": shares,
                "entry_price": entry_price,
                "current_price": entry_price,  # Initially same as entry
                "entry_time": datetime.now(timezone.utc),
                "market_name": market_id,
            }
            log_info(
                f"📍 Position opened: {market_id} {side} {shares:.2f} @ ${entry_price:.4f}"
            )

    def update_position_price(
        self, market_id: str, current_price: float
    ) -> Dict[str, Any]:
        """Update current price and calculate unrealized P&L."""
        with self.lock:
            if market_id not in self.positions:
                return {}

            pos = self.positions[market_id]
            pos["current_price"] = current_price  # Store for later display
            entry_price = pos["entry_price"]
            shares = pos["shares"]
            side = pos["side"]

            # Calculate unrealized P&L
            if side == "yes":
                unrealized_pnl = (current_price - entry_price) * shares
            else:  # no
                unrealized_pnl = (entry_price - current_price) * shares

            unrealized_pct = (
                (unrealized_pnl / (entry_price * shares)) * 100
                if entry_price > 0
                else 0
            )

            return {
                "market_id": market_id,
                "side": side,
                "shares": shares,
                "entry_price": entry_price,
                "current_price": current_price,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pct": unrealized_pct,
            }

    def close_position(
        self, market_id: str, exit_price: float, reason: str = "Market closed"
    ) -> Dict[str, Any] | None:
        """Close a position and realize P&L."""
        with self.lock:
            if market_id not in self.positions:
                return None

            pos = self.positions.pop(market_id)
            entry_price = pos["entry_price"]
            shares = pos["shares"]
            side = pos["side"]

            # Calculate realized P&L
            if side == "yes":
                realized_pnl = (exit_price - entry_price) * shares
            else:  # no
                realized_pnl = (entry_price - exit_price) * shares

            realized_pct = (
                (realized_pnl / (entry_price * shares)) * 100
                if entry_price > 0
                else 0
            )

            closed = {
                "market_id": market_id,
                "side": side,
                "shares": shares,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "entry_time": pos["entry_time"],
                "exit_time": datetime.now(timezone.utc),
                "realized_pnl": realized_pnl,
                "realized_pct": realized_pct,
                "reason": reason,
            }
            self.closed_positions.append(closed)

            color = "green" if realized_pnl >= 0 else "red"
            log_info(
                f"📊 Position closed: {market_id} {side} {shares:.2f} @ ${exit_price:.4f} | "
                f"[{color}]P&L: ${realized_pnl:.2f} ({realized_pct:.1f}%)[/{color}]"
            )
            return closed

    def get_all_positions(self) -> List[Dict[str, Any]]:
        """Get current open positions."""
        with self.lock:
            return list(self.positions.values())

    def update_prices_from_market(self, market: Dict[str, Any]) -> None:
        """Update prices for positions based on market data (with yes/no prices)."""
        if "id" not in market or not ("yes" in market and "no" in market):
            return

        market_id = market["id"]
        with self.lock:
            if market_id not in self.positions:
                return

            pos = self.positions[market_id]
            side = pos["side"]

            # Get the appropriate price for the position's side
            current_price = market.get(side, pos["entry_price"])
            pos["current_price"] = current_price

    def get_summary(self) -> Dict[str, Any]:
        """Get overall P&L summary."""
        with self.lock:
            total_realized = sum(p.get("realized_pnl", 0) for p in self.closed_positions)
            return {
                "open_positions": len(self.positions),
                "closed_positions": len(self.closed_positions),
                "total_realized_pnl": total_realized,
                "closed_position_list": self.closed_positions[-10:],  # Last 10
            }



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
