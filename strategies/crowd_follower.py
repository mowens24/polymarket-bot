# strategies/crowd_follower.py - Strategy logic with adaptive vig tolerance

from typing import Optional, Tuple

from config import (
    MAX_BET_USD,
    MAX_THRESHOLD,
    MIN_THRESHOLD,
    MIN_VOLUME,
    PREFERRED_SIDE,
    get_vig_tolerance,
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
                "MAX_BET_USD": MAX_BET_USD,
            },
        )()

    def scan_for_edge(
        self, market: dict
    ) -> Tuple[Tuple[float, float], float, float, Optional[str], Optional[dict]]:
        """Scan for edge WITHOUT executing. Returns (prices, vig, vol, edge_msg, edge_details)."""
        yes_price, no_price, yes_token, no_token = get_token_prices(self.client, market)
        vig = yes_price + no_price
        vol = float(market.get("volume", 0))

        # Skip low-liquidity markets
        if vol < MIN_VOLUME:
            log_info(f"Volume {vol} below MIN_VOLUME {MIN_VOLUME} - skipping")
            return (yes_price, no_price), vig, vol, None, None

        log_info(f"Market: {market['question'][:70]}...")
        log_info(
            f"Yes (Up): ${yes_price:.4f} | No (Down): ${no_price:.4f} | Vig: {vig:.3f}"
        )

        # Use adaptive vig tolerance based on volume
        vig_tolerance = get_vig_tolerance(vol)
        if not (vig_tolerance[0] <= vig <= vig_tolerance[1]):
            log_info(
                f"Vig {vig:.3f} out of range {vig_tolerance} for volume {vol:.0f} - skipping"
            )
            return (yes_price, no_price), vig, vol, None, None

        candidates = []
        if self.config.MIN_THRESHOLD <= yes_price <= self.config.MAX_THRESHOLD:
            candidates.append(("yes", yes_price, yes_token))
        if self.config.MIN_THRESHOLD <= no_price <= self.config.MAX_THRESHOLD:
            candidates.append(("no", no_price, no_token))

        if not candidates:
            # log_info("No lopsided edge - waiting...")
            return (yes_price, no_price), vig, vol, None, None

        # Pick strongest (highest price), prefer PREFERRED_SIDE on tie
        candidates.sort(
            key=lambda x: (-x[1], 0 if x[0] == self.config.PREFERRED_SIDE else 1)
        )
        side_name, price, token_id = candidates[0]

        amount = fixed_sizing()
        edge_msg = f"Buying {side_name.upper()} @ ${price:.4f} for ${amount:.2f}"
        log_info(f"EDGE FOUND: {edge_msg}")

        edge_details = {
            "side": side_name,
            "price": price,
            "token_id": token_id,
            "amount": amount,
        }

        return (yes_price, no_price), vig, vol, edge_msg, edge_details

    def execute_edge(self, edge_details: dict, market: dict) -> bool:
        """Execute a found edge. Returns True if executed successfully."""
        if not edge_details:
            return False

        side_name = edge_details["side"]
        token_id = edge_details["token_id"]
        amount = edge_details["amount"]
        price = edge_details["price"]

        # Ensure token id is present before attempting execution
        if token_id is None:
            log_info("Missing token id for selected side - skipping execution")
            return False

        execute_market_buy(self.client, token_id, amount, side_name, market, price)
        return True

    def scan_and_get_status(
        self, market: dict
    ) -> Tuple[Tuple[float, float], float, float, Optional[str]]:
        prices, vig, vol, edge_msg, _ = self.scan_for_edge(market)
        return prices, vig, vol, edge_msg

    def scan_and_execute(self, market: dict) -> None:
        # Just delegate to the new method for compatibility
        self.scan_and_get_status(market)
