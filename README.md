# Polymarket 15m BTC Bot

This repository contains a crowd-following trading bot for 15-minute BTC markets on Polymarket with advanced risk management, monitoring, and safety features.

[![CI](https://github.com/mowens24/polymarket-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/mowens24/polymarket-bot/actions/workflows/ci.yml)

## Features

- **Adaptive Market Analysis**: Adjusts vig tolerance based on market volume
- **Position Limits**: Prevents overleveraging with cumulative exposure tracking
- **Real-time Monitoring**: Trade metrics, loss tracking, and anomaly alerts
- **Data Persistence**: SQLite database for trade history and market snapshots
- **Safety Checks**: Wallet balance validation, partial fill detection, retry logic
- **DRY RUN Mode**: Paper portfolio simulation before going live
- **Multi-tier Config**: Dev, staging, and production configurations

## Quickstart

### 1. Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration

Add your private key to `.env`:

```bash
POLYGON_PRIVATE_KEY=0x...
```

Select environment tier:

```bash
export BOT_ENV=dev      # Default: loose thresholds, DRY_RUN=True
export BOT_ENV=stage    # Medium thresholds, DRY_RUN=True
export BOT_ENV=prod     # Conservative thresholds, DRY_RUN=False (when ready)
```

### 3. Validate & Test

```bash
# Validate configuration
python3 cli.py validate

# Quick market scan
python3 cli.py scan-once

# Run tests
pytest -q
```

### 4. Run the Bot

```bash
python3 main.py
```

## Configuration Tiers

### Development (`config_dev.py`)
- `DRY_RUN = True` (no real trades)
- Loose thresholds for testing
- MIN_VOLUME: 500 (accepts illiquid markets)
- MAX_BET_USD: 0.50

### Staging (`config_stage.py`)
- `DRY_RUN = True` (simulation mode)
- Medium thresholds
- MIN_VOLUME: 2,000
- MAX_BET_USD: 1.00

### Production (`config_prod.py`)
- `DRY_RUN = False` (real trades when enabled)
- Conservative thresholds
- MIN_VOLUME: 10,000 (high liquidity only)
- MAX_BET_USD: 2.50

## Key Modules

### Core Strategy
- `main.py` - Live dashboard with real-time market updates
- `strategies/crowd_follower.py` - Adaptive strategy with volume-based vig tolerance
- `client.py`, `pricing.py`, `markets.py` - Polymarket data layer

### Risk Management
- `risk/position_limits.py` - Position tracking & cumulative exposure limits
- `config.py` - Centralized, validated configuration
- `execution.py` - Safe order execution with wallet checks & retries

### Monitoring & Persistence
- `monitoring.py` - Trade metrics, loss tracking, anomaly alerts
- `data_store.py` - SQLite trade history and market snapshots
- `logger.py` - Structured JSON logging to `bot.log`

### Tools
- `cli.py` - CLI for quick checks and testing
- `btc_bot.py` - Lightweight market scanner
- `tools/legacy_btc_bot.py` - Original full implementation (archived)

## Safety Features

✅ **Wallet Balance Check** - Validates sufficient funds before trading
✅ **Position Limits** - Prevents exceeding max concurrent positions & daily trades
✅ **Loss Alerts** - Warns when daily loss exceeds limit or loss streak detected
✅ **Partial Fill Detection** - Alerts if order doesn't fill >= 95%
✅ **Retry Logic** - Exponential backoff (3 attempts, max 4s wait) for failed orders
✅ **DRY RUN Mode** - Simulates trades with paper portfolio before going live

## Testing

```bash
# Run all tests
pytest -v

# Run integration tests only
pytest tests/test_integration.py -v

# Run with coverage
pytest --cov=. tests/
```

## Database

Trade history stored in `bot_history.db`:
- `trades` - All executed orders with P&L
- `market_snapshots` - Market state at decision time

Query recent trades:
```python
from data_store import TradeDatabase
db = TradeDatabase()
stats = db.get_trade_stats(days=1)
print(stats)
```

## Logs

Structured JSON logs written to `bot.log`:
```json
{"timestamp": "2025-01-08T15:30:45", "level": "INFO", "message": "Volume 5000 below MIN_VOLUME..."}
```

## Development

### Code Quality
- **Linting**: `ruff check` & `ruff format`
- **Type Checking**: `mypy` (Python 3.11+)
- **Pre-commit Hooks**: Auto-format & lint on commit

### Adding Tests
```python
# tests/test_custom.py
def test_my_feature():
    from my_module import my_function
    assert my_function() == expected
```

## Notes

- The bot defaults to `DRY_RUN = True` in all configs
- For live trading, export `BOT_ENV=prod` and set `DRY_RUN = False` in `config_prod.py`
- Keep `.env` secret (add to `.gitignore`)
- Monitor `bot.log` and `bot_history.db` for diagnostics
- All position sizes are controlled by `MAX_BET_USD` per config tier

## Improvements & Roadmap

Recent additions (v1.1):
- ✅ Adaptive vig tolerance (tight for high volume, loose for low volume)
- ✅ Position limit tracking & enforcement
- ✅ Trade metrics with loss alerts
- ✅ SQLite persistence for audit trail
- ✅ Wallet balance validation
- ✅ Multi-tier configuration (dev/stage/prod)

Future enhancements:
- Async multi-market concurrency
- P&L reconciliation with blockchain
- Advanced risk models (Sharpe ratio, drawdown limits)
- Backtesting framework
- Webhook alerts for critical events

## License

MIT
