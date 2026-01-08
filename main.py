# main.py - Entry point with fancy Rich live dashboard + time left progress bar

import sys
import time
from typing import Optional

from rich.live import Live

from client import get_client
from config import SCAN_INTERVAL, validate_config
from data_store import TradeDatabase
from execution import check_wallet_balance
from logger import console, get_status_panel
from markets import fetch_current_15min_btc_market
from monitoring import TradeMetrics
from risk.position_limits import PositionLimits
from strategies.crowd_follower import CrowdFollowerStrategy

# Global to track current slot unix (set in loop)
current_slot_unix: Optional[int] = None

# Initialize persistence and monitoring
_db = TradeDatabase()
_metrics = TradeMetrics()
_position_limits = PositionLimits()


def main():
    # Validate configuration before starting runtime components
    cfg_errors = validate_config()
    if cfg_errors:
        for e in cfg_errors:
            console.print(f"[bold red]CONFIG ERROR:[/bold red] {e}")
        sys.exit(1)

    console.print("[bold green]Crowd-following bot STARTED[/bold green]")
    client = get_client()

    # Check wallet at startup
    check_wallet_balance(client)

    strategy = CrowdFollowerStrategy(client)

    global current_slot_unix

    with Live(
        get_status_panel(
            None, (0.5, 0.5), 1.000, 0.0, edge=None, time_left=900, total_time=900
        ),
        refresh_per_second=4,
        console=console,
    ) as live:
        while True:
            market = fetch_current_15min_btc_market()
            if market:
                # Get status from strategy
                prices, vig, vol, edge_msg = strategy.scan_and_get_status(market)

                # Update current slot unix for time left calc
                if "slug" in market:
                    try:
                        current_slot_unix = int(market["slug"].split("-")[-1])
                    except Exception:
                        current_slot_unix = int(time.time() // 900 * 900)  # fallback

                # Calculate time left in slot
                utc_now = time.time()
                if current_slot_unix is None:
                    time_left = 900
                else:
                    time_left = max(0, 900 - (int(utc_now) - current_slot_unix))

                live.update(
                    get_status_panel(
                        market=market,
                        prices=prices,
                        vig=vig,
                        vol=vol,
                        edge=edge_msg,
                        time_left=time_left,
                        total_time=900,
                    )
                )

                # Record market snapshot if edge was found
                if edge_msg and "id" in market:
                    _db.record_market_snapshot(
                        market["id"], market, prices[0], prices[1], vig, vol
                    )

            else:
                live.update(
                    get_status_panel(
                        None,
                        (0.5, 0.5),
                        1.000,
                        0.0,
                        edge=None,
                        time_left=900,
                        total_time=900,
                    )
                )
                current_slot_unix = None

            time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    main()
