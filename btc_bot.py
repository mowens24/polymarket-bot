"""Lightweight CLI for quick BTC market checks.

This script is a small, user-friendly replacement for the older heavy
`btc_bot.py` script. For the original full bot implementation see
`tools/legacy_btc_bot.py`.
"""

from __future__ import annotations

import argparse
from typing import Optional

from rich.console import Console

from markets import fetch_current_15min_btc_market
from pricing import get_token_prices

console = Console()


def cmd_scan_once(args: Optional[argparse.Namespace] = None) -> None:
    """Scan and display current 15-min BTC market."""
    market = fetch_current_15min_btc_market()
    if not market:
        console.print("[yellow]No active 15-min BTC market found.[/yellow]")
        return

    prices = get_token_prices(None, market)
    yes_price, no_price = prices[0], prices[1]
    vol = float(market.get("volume", 0))
    vig = yes_price + no_price

    console.print(f"[bold magenta]{market.get('question', 'Unknown')}[/bold magenta]")
    console.print(f"Volume: [yellow]${vol:,.2f}[/yellow]")
    console.print(
        f"Yes: [green]{yes_price:.4f}[/green]  No: [red]{no_price:.4f}[/red]"
    )
    console.print(f"Vig: [cyan]{vig:.3f}[/cyan]")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(prog="btc-bot")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser(
        "scan-once", help="Fetch and print the current 15-min BTC market summary"
    )

    args = parser.parse_args()
    if args.cmd == "scan-once":
        cmd_scan_once(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
