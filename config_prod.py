"""Production config: conservative thresholds for live trading."""

DRY_RUN = False
MAX_BET_USD = 2.50
MIN_THRESHOLD = 0.70
MAX_THRESHOLD = 0.98
PREFERRED_SIDE = "yes"
VIG_TOLERANCE_TIGHT = (0.98, 1.02)  # High volume
VIG_TOLERANCE_LOOSE = (0.95, 1.05)  # Low volume
MIN_VOLUME = 10000  # Higher threshold for prod
SCAN_INTERVAL = 60

# Safety limits
DAILY_LOSS_LIMIT_USD = 50.0
MAX_DAILY_TRADES = 20
MAX_POSITION_USD = 100.0
MAX_CONCURRENT_POSITIONS = 5
WALLET_MIN_BALANCE_USD = 10.0
