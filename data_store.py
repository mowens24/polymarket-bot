"""SQLite-based trade history and market snapshot storage."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from logger import log_error, log_info


class TradeDatabase:
    """Persistent storage for trades and market snapshots."""

    def __init__(self, db_path: str = "bot_history.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Create database tables if they don't exist."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS trades (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        market_id TEXT NOT NULL,
                        market_question TEXT,
                        side TEXT NOT NULL,
                        amount_usd REAL NOT NULL,
                        price REAL NOT NULL,
                        is_dry_run INTEGER NOT NULL,
                        pnl_usd REAL,
                        tx_hash TEXT
                    )
                    """
                )
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS market_snapshots (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        market_id TEXT NOT NULL,
                        market_data TEXT NOT NULL,
                        yes_price REAL NOT NULL,
                        no_price REAL NOT NULL,
                        vig REAL NOT NULL,
                        volume REAL NOT NULL
                    )
                    """
                )
                conn.commit()
                log_info(f"Database initialized: {self.db_path}")
        except Exception as e:
            log_error(f"Database init failed: {e}")

    def record_trade(
        self,
        market_id: str,
        market_question: str,
        side: str,
        amount_usd: float,
        price: float,
        is_dry_run: bool,
        tx_hash: Optional[str] = None,
    ) -> None:
        """Record a trade to database."""

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO trades
                    (timestamp, market_id, market_question, side, amount_usd, price,
                     is_dry_run, tx_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        datetime.now(timezone.utc).isoformat(),
                        market_id,
                        market_question,
                        side,
                        amount_usd,
                        price,
                        int(is_dry_run),
                        tx_hash,
                    ),
                )
                conn.commit()
        except Exception as e:
            log_error(f"Trade record failed: {e}")

    def record_market_snapshot(
        self,
        market_id: str,
        market_data: dict,
        yes_price: float,
        no_price: float,
        vig: float,
        volume: float,
    ) -> None:
        """Record market state at decision time."""

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO market_snapshots
                    (timestamp, market_id, market_data, yes_price, no_price, vig, volume)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        datetime.now(timezone.utc).isoformat(),
                        market_id,
                        json.dumps(market_data),
                        yes_price,
                        no_price,
                        vig,
                        volume,
                    ),
                )
                conn.commit()
        except Exception as e:
            log_error(f"Market snapshot record failed: {e}")

    def get_recent_trades(self, limit: int = 10) -> List[dict]:
        """Get recent trades from database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT * FROM trades ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            log_error(f"Query recent trades failed: {e}")
            return []

    def get_trade_stats(self, days: int = 1) -> dict:
        """Get aggregate trading stats."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        SUM(CASE WHEN is_dry_run = 1 THEN 1 ELSE 0 END) as dry_run,
                        SUM(CASE WHEN is_dry_run = 0 THEN 1 ELSE 0 END) as live,
                        AVG(price) as avg_price,
                        SUM(amount_usd) as total_volume_usd
                    FROM trades
                    WHERE timestamp >= datetime('now', '-' || ? || ' days')
                    """,
                    (days,),
                )
                row = cursor.fetchone()
                if row:
                    return {
                        "total": row[0],
                        "dry_run": row[1],
                        "live": row[2],
                        "avg_price": row[3],
                        "total_volume_usd": row[4],
                    }
                return {}
        except Exception as e:
            log_error(f"Trade stats query failed: {e}")
            return {}
