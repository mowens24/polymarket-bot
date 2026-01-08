# config.py - All tunable parameters in one place
# Load environment-specific config (dev, stage, prod)
import os

_ENV = os.getenv("BOT_ENV", "dev").lower()

if _ENV == "prod":
    from config_prod import *  # noqa: F401,F403
elif _ENV == "stage":
    from config_stage import *  # noqa: F401,F403
else:
    # Default to dev
    DRY_RUN = True  # Set to False when ready to go live
    MAX_BET_USD = 0.50
    MIN_THRESHOLD = 0.30
    MAX_THRESHOLD = 0.90
    PREFERRED_SIDE = "yes"  # Bias toward Up (Yes) on ties
    VIG_TOLERANCE_TIGHT = (0.98, 1.02)  # High volume markets
    VIG_TOLERANCE_LOOSE = (0.90, 1.10)  # Low volume markets
    MIN_VOLUME = 500
    SCAN_INTERVAL = 10

    # Safety limits
    DAILY_LOSS_LIMIT_USD = 200.0
    MAX_DAILY_TRADES = 100
    MAX_POSITION_USD = 25.0
    MAX_CONCURRENT_POSITIONS = 20
    WALLET_MIN_BALANCE_USD = 1.0


# Helper function to get vig tolerance based on volume
def get_vig_tolerance(volume: float, high_volume_threshold: float = 10000.0) -> tuple:
    """Return vig tolerance range based on market volume."""
    try:
        if volume >= high_volume_threshold:
            return VIG_TOLERANCE_TIGHT
        else:
            return VIG_TOLERANCE_LOOSE
    except NameError:
        return (0.95, 1.05)  # Fallback


def validate_config() -> list:
    """Validate configuration at startup."""
    errors = []

    # Check if required variables are defined in the loaded config
    required_vars = [
        "DRY_RUN",
        "MAX_BET_USD",
        "MIN_THRESHOLD",
        "MAX_THRESHOLD",
        "PREFERRED_SIDE",
        "MIN_VOLUME",
        "SCAN_INTERVAL",
    ]

    for var_name in required_vars:
        try:
            globals()[var_name]
        except KeyError:
            errors.append(f"Missing config variable: {var_name}")

    if errors:
        return errors

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
            lambda: isinstance(MIN_VOLUME, int) and MIN_VOLUME >= 0,
            "MIN_VOLUME must be non-negative integer",
        ),
        (
            lambda: isinstance(SCAN_INTERVAL, int) and SCAN_INTERVAL > 0,
            "SCAN_INTERVAL must be a positive integer",
        ),
        (
            lambda: isinstance(DAILY_LOSS_LIMIT_USD, (int, float)) and DAILY_LOSS_LIMIT_USD > 0,
            "DAILY_LOSS_LIMIT_USD must be > 0",
        ),
        (
            lambda: isinstance(MAX_POSITION_USD, (int, float)) and MAX_POSITION_USD > 0,
            "MAX_POSITION_USD must be > 0",
        ),
        (
            lambda: isinstance(WALLET_MIN_BALANCE_USD, (int, float)) and WALLET_MIN_BALANCE_USD >= 0,
            "WALLET_MIN_BALANCE_USD must be >= 0",
        ),
    ]

    for pred, msg in checks:
        try:
            if not pred():
                errors.append(msg)
        except Exception as e:
            errors.append(f"Config check failed: {e}")

    return errors
