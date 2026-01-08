# strategies/crowd_follower.py - Strategy logic

from typing import Optional, Tuple

from config import (
    MAX_BET_USD,
    MAX_THRESHOLD,
    MIN_THRESHOLD,
    MIN_VOLUME,
    PREFERRED_SIDE,
    VIG_TOLERANCE_HIGH,
    VIG_TOLERANCE_LOW,
)
from execution import execute_market_buy
from logger import log_info
from pricing import get_token_prices
from risk.position_sizing import fixed_sizing


class CrowdFollowerStrategy:
    def __init__(self, client):
        self.client = client
        # Load config values for easy access
        self.config = type(
            "config",
            (),
            {
                "MIN_THRESHOLD": MIN_THRESHOLD,
                "MAX_THRESHOLD": MAX_THRESHOLD,
                "PREFERRED_SIDE": PREFERRED_SIDE,
                "VIG_TOLERANCE_LOW": VIG_TOLERANCE_LOW,
                "VIG_TOLERANCE_HIGH": VIG_TOLERANCE_HIGH,
                "MAX_BET_USD": MAX_BET_USD,
            },
        )()

    def scan_and_execute(self, market: dict) -> None:
        # Just delegate to the new method for compatibility
        self.scan_and_get_status(market)

    def scan_and_get_status(
        self, market: dict
    ) -> Tuple[Tuple[float, float], float, float, Optional[str]]:
        yes_price, no_price, yes_token, no_token = get_token_prices(self.client, market)
        vig = yes_price + no_price
        vol = float(market.get("volume", 0))

        # Skip low-liquidity markets
        if vol < MIN_VOLUME:
            log_info(f"Volume {vol} below MIN_VOLUME {MIN_VOLUME} - skipping")
            return (yes_price, no_price), vig, vol, None

        log_info(f"Market: {market['question'][:70]}...")
        log_info(
            f"Yes (Up): ${yes_price:.4f} | No (Down): ${no_price:.4f} | Vig: {vig:.3f}"
        )

        if not (self.config.VIG_TOLERANCE_LOW <= vig <= self.config.VIG_TOLERANCE_HIGH):
            log_info("Vig out of range - skipping")
            return (yes_price, no_price), vig, vol, None

        candidates = []
        if self.config.MIN_THRESHOLD <= yes_price <= self.config.MAX_THRESHOLD:
            candidates.append(("yes", yes_price, yes_token))
        if self.config.MIN_THRESHOLD <= no_price <= self.config.MAX_THRESHOLD:
            candidates.append(("no", no_price, no_token))

        if not candidates:
            # log_info("No lopsided edge - waiting...")
            return (yes_price, no_price), vig, vol, None

        # Pick strongest (highest price), prefer PREFERRED_SIDE on tie
        candidates.sort(
            key=lambda x: (-x[1], 0 if x[0] == self.config.PREFERRED_SIDE else 1)
        )
        side_name, price, token_id = candidates[0]

        amount = fixed_sizing()
        edge_msg = f"Buying {side_name.upper()} @ ${price:.4f} for ${amount:.2f}"
        log_info(f"EDGE FOUND: {edge_msg}")

        # Ensure token id is present before attempting execution
        if token_id is None:
            log_info("Missing token id for selected side - skipping execution")
        else:
            execute_market_buy(self.client, token_id, amount, side_name, market, price)

        return (yes_price, no_price), vig, vol, edge_msg
