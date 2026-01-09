# main.py - Entry point with fancy Rich live dashboard + real-time P&L monitoring

import sys
import time
from typing import Optional

from rich.live import Live

from client import get_client
from config import SCAN_INTERVAL, validate_config
from data_store import TradeDatabase
from execution import check_wallet_balance, set_position_monitor
from logger import console, get_pnl_panel, get_status_panel, log_info
from markets import fetch_current_15min_btc_market
from monitoring import PositionMonitor, TradeMetrics
from risk.position_limits import PositionLimits
from strategies.crowd_follower import CrowdFollowerStrategy, is_price_acceptable

# Global to track current slot unix (set in loop)
current_slot_unix: Optional[int] = None
last_traded_market_id: Optional[str] = None  # Prevent duplicate trades in same slot

# Initialize persistence, monitoring, and position tracking
_db = TradeDatabase()
_metrics = TradeMetrics()
_position_limits = PositionLimits()
_position_monitor = PositionMonitor()


def _process_market_cycle(market, strategy, position_monitor, position_limits, metrics, db):
    """Process a single market scan cycle and update global trade state."""
    global current_slot_unix, last_traded_market_id

    market_id = market.get("id")
    # Use the correct field names from Gamma API (yes_price, no_price)
    yes_price = float(market.get("yes_price", 0.5))
    no_price = float(market.get("no_price", 0.5))
    prices = (yes_price, no_price)
    vig = yes_price + no_price
    vol = float(market.get("volume", 0))

    # Update position prices with current market data
    position_monitor.update_prices_from_market(
        {"id": market_id, "yes": yes_price, "no": no_price}
    )

    # Detect slot change
    new_slot = current_slot_unix
    if "slug" in market:
        try:
            new_slot = int(market["slug"].split("-")[-1])
        except Exception:
            new_slot = int(time.time() // 900 * 900)

    if new_slot != current_slot_unix:
        log_info("📍 New slot detected, resetting trade tracker")
        last_traded_market_id = None
        current_slot_unix = new_slot

    # Calculate time left
    utc_now = time.time()
    time_left = 900
    if current_slot_unix is not None:
        time_left = max(0, 900 - (int(utc_now) - current_slot_unix))

    # Check if we should trade this market
    edge_msg = None
    if market_id != last_traded_market_id:
        _, _, _, edge_msg, edge_details = strategy.scan_for_edge(market)
        if edge_details:
            price = edge_details.get("price", 0.0)
            # Check price floor before executing
            if is_price_acceptable(price):
                strategy.execute_edge(edge_details, market)
                last_traded_market_id = market_id
                log_info(f"🔥 Trade executed at ${price:.4f}, locking market {market_id[:16]} for this slot")
            else:
                # Edge found but price too low - don't execute yet
                edge_msg = None
    else:
        log_info(f"✓ Already traded {market_id[:16]} this slot, updating P&L...")

    # Record snapshot if edge found
    if edge_msg and market_id:
        db.record_market_snapshot(market_id, market, yes_price, no_price, vig, vol)

    return prices, vig, vol, edge_msg, time_left


def _update_display(
    market, prices, vig, vol, edge_msg, time_left, position_monitor, position_limits, metrics, db
):
    """Helper to determine which panel to display based on current positions."""
    if position_monitor.get_all_positions():
        return get_pnl_panel(position_monitor)

    return get_status_panel(
        market=market,
        prices=prices,
        vig=vig,
        vol=vol,
        edge=edge_msg,
        time_left=time_left,
        total_time=900,
        position_status=position_limits.get_status(),
        metrics=metrics.get_statistics(),
    )


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

    global current_slot_unix, last_traded_market_id

    # Set the position monitor globally so execution.py can use it
    set_position_monitor(_position_monitor)

    with Live(
        get_status_panel(
            None, (0.5, 0.5), 1.000, 0.0, edge=None, time_left=900, total_time=900
        ),
        refresh_per_second=2,
        console=console,
    ) as live:
        _run_trading_loop(live, strategy)


def _run_trading_loop(live, strategy):
    """Main trading loop."""
    global current_slot_unix, last_traded_market_id

    while True:
        market = fetch_current_15min_btc_market()
        if market:
            # Process market and get updated state
            prices, vig, vol, edge_msg, time_left = (
                _process_market_cycle(
                    market, strategy, _position_monitor, _position_limits, _metrics, _db
                )
            )
            display_panel = _update_display(
                market, prices, vig, vol, edge_msg, time_left,
                _position_monitor, _position_limits, _metrics, _db
            )
            live.update(display_panel)
        else:
            # No market data available
            display_panel = _update_display(
                None, (0.5, 0.5), 1.000, 0.0, None, 900,
                _position_monitor, _position_limits, _metrics, _db
            )
            live.update(display_panel)
            current_slot_unix = None

        time.sleep(SCAN_INTERVAL)


if __name__ == "__main__":
    main()
