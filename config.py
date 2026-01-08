# config.py - All tunable parameters in one place
DRY_RUN = True  # Set to False when ready to go live
MAX_BET_USD = 2.50
MIN_THRESHOLD = 0.70  # Buy only if side >= 60¢
MAX_THRESHOLD = 0.98  # Skip if >98¢ (low ROI)
PREFERRED_SIDE = "yes"  # Bias toward Up (Yes) on ties
VIG_TOLERANCE_LOW = 0.95
VIG_TOLERANCE_HIGH = 1.05
MIN_VOLUME = 5000  # Skip low-liquidity markets
SCAN_INTERVAL = 60  # Seconds between checks


def validate_config() -> list:
    checks = [
        (lambda: isinstance(DRY_RUN, bool), "DRY_RUN must be a boolean"),
        (
            lambda: isinstance(MAX_BET_USD, (int, float)) and MAX_BET_USD > 0,
            "MAX_BET_USD must be > 0",
        ),
        (lambda: 0.0 <= MIN_THRESHOLD <= 1.0, "MIN_THRESHOLD must be between 0.0 and 1.0"),
        (lambda: 0.0 <= MAX_THRESHOLD <= 1.0, "MAX_THRESHOLD must be between 0.0 and 1.0"),
        (
            lambda: MIN_THRESHOLD <= MAX_THRESHOLD,
            "MIN_THRESHOLD cannot be greater than MAX_THRESHOLD",
        ),
        (lambda: PREFERRED_SIDE in ("yes", "no"), "PREFERRED_SIDE must be 'yes' or 'no'"),
        (
            lambda: VIG_TOLERANCE_LOW <= VIG_TOLERANCE_HIGH,
            "VIG_TOLERANCE_LOW cannot be greater than VIG_TOLERANCE_HIGH",
        ),
        (
            lambda: isinstance(MIN_VOLUME, int) and MIN_VOLUME >= 0,
            "MIN_VOLUME must be non-negative integer",
        ),
        (
            lambda: isinstance(SCAN_INTERVAL, int) and SCAN_INTERVAL > 0,
            "SCAN_INTERVAL must be a positive integer",
        ),
    ]

    errors = [msg for pred, msg in checks if not pred()]
    return errors
