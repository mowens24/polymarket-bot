"""Integration tests for execution, position limits, and monitoring."""

import pytest

from config import MAX_CONCURRENT_POSITIONS, MAX_POSITION_USD
from data_store import TradeDatabase
from monitoring import TradeMetrics
from risk.position_limits import PositionLimits


class TestPositionLimits:
    """Test position tracking and limit enforcement."""

    def test_can_trade_basic(self):
        """Test basic trade approval."""
        limits = PositionLimits()
        assert limits.can_trade("market_1", 10.0)

    def test_position_size_limit(self):
        """Test that oversized positions are rejected."""
        limits = PositionLimits()
        assert not limits.can_trade("market_1", MAX_POSITION_USD + 1.0)

    def test_daily_trade_limit(self):
        """Test daily trade count limit."""
        from config import MAX_DAILY_TRADES

        limits = PositionLimits()
        limits.daily_trade_count = MAX_DAILY_TRADES
        assert not limits.can_trade("market_1", 5.0)

    def test_concurrent_position_limit(self):
        """Test max concurrent positions."""
        limits = PositionLimits()
        for i in range(MAX_CONCURRENT_POSITIONS):
            limits.add_position(f"market_{i}", 10.0)
        # Next position should be rejected
        assert not limits.can_trade("market_new", 10.0)

    def test_add_and_close_position(self):
        """Test adding and closing positions."""
        limits = PositionLimits()
        limits.add_position("market_1", 25.0)
        assert limits.total_exposure_usd == 25.0
        assert len(limits.active_positions) == 1

        limits.close_position("market_1", pnl_usd=2.5)
        assert limits.total_exposure_usd == 0.0
        assert len(limits.active_positions) == 0

    def test_exposure_tracking(self):
        """Test cumulative exposure tracking."""
        limits = PositionLimits()
        limits.add_position("market_1", 10.0)
        limits.add_position("market_2", 15.0)
        limits.add_position("market_3", 20.0)
        assert limits.total_exposure_usd == 45.0


class TestTradeMetrics:
    """Test trade metrics and loss tracking."""

    def test_record_trade(self):
        """Test recording a trade."""
        metrics = TradeMetrics()
        metrics.record_trade("market_1", "yes", 10.0, 0.65)
        assert len(metrics.trades) == 1

    def test_pnl_tracking(self):
        """Test P&L recording."""
        metrics = TradeMetrics(loss_limit_usd=50.0)
        metrics.record_pnl("market_1", 5.0)  # Win
        assert metrics.loss_streak == 0

        metrics.record_pnl("market_2", -10.0)  # Loss
        assert metrics.loss_streak == 1
        assert metrics.daily_loss_usd == 10.0

    def test_loss_streak_alert(self):
        """Test loss streak detection."""
        metrics = TradeMetrics(loss_streak_alert=2)
        metrics.record_pnl("m1", -5.0)
        assert metrics.loss_streak == 1
        metrics.record_pnl("m2", -5.0)
        assert metrics.loss_streak == 2

    def test_reset_daily_stats(self):
        """Test resetting daily metrics."""
        metrics = TradeMetrics()
        metrics.record_pnl("m1", -10.0)
        assert metrics.daily_loss_usd == 10.0
        metrics.reset_daily_stats()
        assert metrics.daily_loss_usd == 0.0

    def test_get_statistics(self):
        """Test stats aggregation."""
        metrics = TradeMetrics()
        metrics.record_trade("m1", "yes", 10.0, 0.65, is_dry_run=True)
        metrics.record_trade("m2", "no", 10.0, 0.35, is_dry_run=False)
        stats = metrics.get_statistics()
        assert stats["total_trades"] == 2
        assert stats["dry_run_trades"] == 1
        assert stats["live_trades"] == 1


class TestTradeDatabase:
    """Test database persistence."""

    def test_database_init(self, tmp_path):
        """Test database initialization."""
        db_path = str(tmp_path / "test.db")
        db = TradeDatabase(db_path)
        assert db.db_path.exists()

    def test_record_trade(self, tmp_path):
        """Test recording trade to database."""
        db_path = str(tmp_path / "test.db")
        db = TradeDatabase(db_path)
        db.record_trade("market_1", "Test Market", "yes", 10.0, 0.65, False, "tx_123")
        trades = db.get_recent_trades(limit=1)
        assert len(trades) > 0
        assert trades[0]["side"] == "yes"

    def test_record_market_snapshot(self, tmp_path):
        """Test recording market snapshot."""
        db_path = str(tmp_path / "test.db")
        db = TradeDatabase(db_path)
        market_data = {"id": "m1", "question": "Will BTC go up?"}
        db.record_market_snapshot("market_1", market_data, 0.65, 0.35, 1.0, 5000.0)
        # Just verify no exception is raised
        assert True

    def test_get_trade_stats(self, tmp_path):
        """Test trade statistics query."""
        db_path = str(tmp_path / "test.db")
        db = TradeDatabase(db_path)
        db.record_trade("m1", "Test", "yes", 10.0, 0.65, True)
        stats = db.get_trade_stats()
        assert stats.get("total") == 1


class TestExecutionSafety:
    """Test execution safety checks."""

    def test_position_limit_guards_execution(self):
        """Test that execution respects position limits."""
        limits = PositionLimits()
        limits.daily_trade_count = 100  # Set high

        # Set up a position that approaches limit
        for i in range(MAX_CONCURRENT_POSITIONS - 1):
            limits.add_position(f"m_{i}", 20.0)

        # Next trade should be blocked due to position count
        assert not limits.can_trade("m_new", 20.0)

    def test_metrics_alert_on_loss_limit(self):
        """Test metrics alert when loss limit is breached."""
        from config import DAILY_LOSS_LIMIT_USD

        metrics = TradeMetrics(loss_limit_usd=DAILY_LOSS_LIMIT_USD)

        # Record multiple losses that exceed limit
        loss_per_trade = DAILY_LOSS_LIMIT_USD / 2 + 1
        metrics.record_pnl("m1", -loss_per_trade)
        metrics.record_pnl("m2", -loss_per_trade)

        # Daily loss should exceed limit
        assert metrics.daily_loss_usd > DAILY_LOSS_LIMIT_USD


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
