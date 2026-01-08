# Polymarket 15m BTC Bot

This repository contains a crowd-following trading bot for 15-minute BTC markets on Polymarket.

[![CI](https://github.com/mowens24/polymarket-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/mowens24/polymarket-bot/actions/workflows/ci.yml)

Quickstart

1. Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

2. Add your private key to `.env` (do NOT commit this file):

```
POLYGON_PRIVATE_KEY=0x...
```

3. Validate config and run a dry scan:

```bash
python3 cli.py validate
python3 cli.py scan-once
```

4. Run tests:

```bash
pytest -q
```

Notes
- The bot defaults to `DRY_RUN = True` in `config.py`. Set to `False` for live orders.
- Logs are written to `bot.log` for diagnostics.
