#!/usr/bin/env python3
"""Simple CLI for runtime checks and dry-run scans."""

import argparse
import os
import shutil
import subprocess
from datetime import datetime

from logger import console


def cmd_validate(args):
    from config import validate_config

    errors = validate_config()
    if errors:
        for e in errors:
            console.print(f"[bold red]CONFIG ERROR:[/bold red] {e}")
        raise SystemExit(1)
    console.print("[bold green]✅ Config OK[/bold green]")


def cmd_scan_once(args):
    from client import get_client
    from markets import fetch_current_15min_btc_market
    from strategies.crowd_follower import CrowdFollowerStrategy

    client = get_client()
    market = fetch_current_15min_btc_market()
    if not market:
        console.print("[bold yellow]No active market found[/bold yellow]")
        return

    strategy = CrowdFollowerStrategy(client)
    status = strategy.scan_and_get_status(market)
    console.print(f"[bold cyan]Scan result:[/bold cyan] {status}")


def cmd_run_tests(args):
    console.print("[bold cyan]Running pytest...[/bold cyan]")
    res = subprocess.run(["pytest", "-q"], cwd=None)
    raise SystemExit(res.returncode)


def cmd_db_stats(args):
    """Show database trade statistics."""
    from data_store import TradeDatabase

    db = TradeDatabase()
    stats = db.get_trade_stats(days=args.days)

    console.print(f"\n[bold cyan]Trade Stats (last {args.days} day(s)):[/bold cyan]")
    if stats:
        for key, val in stats.items():
            console.print(f"  {key}: {val}")
    else:
        console.print("[yellow]No trades recorded.[/yellow]")

    # Show recent trades
    recent = db.get_recent_trades(limit=5)
    if recent:
        console.print("\n[bold cyan]Last 5 trades:[/bold cyan]")
        for trade in recent:
            console.print(
                f"  {trade['timestamp']}: {trade['side'].upper()} ${trade['amount_usd']:.2f} @ ${trade['price']:.4f}"
            )
    else:
        console.print("[yellow]No recent trades.[/yellow]")


def cmd_db_backup(args):
    """Backup and optionally reset the trade database."""
    db_file = "bot_history.db"
    if not os.path.exists(db_file):
        console.print(f"[yellow]{db_file} not found.[/yellow]")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"bot_history.{timestamp}.bak"
    shutil.copy(db_file, backup_file)
    console.print(f"[bold green]✅ Database backed up to {backup_file}[/bold green]")

    if args.reset:
        os.remove(db_file)
        console.print("[bold green]✅ Database reset (old file removed)[/bold green]")


def cmd_log_rotate(args):
    """Backup and reset the log file."""
    log_file = "bot.log"
    if not os.path.exists(log_file):
        console.print(f"[yellow]{log_file} not found.[/yellow]")
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"bot.{timestamp}.log"
    shutil.copy(log_file, backup_file)
    console.print(f"[bold green]✅ Log backed up to {backup_file}[/bold green]")

    if args.reset:
        open(log_file, "w").close()
        console.print("[bold green]✅ Log file reset[/bold green]")


def cmd_toggle_dry_run(args):
    """Toggle DRY_RUN mode in config."""
    console.print("[bold yellow]⚠️  DRY_RUN toggle is a manual process:[/bold yellow]")
    console.print("  1. Edit config_dev.py, config_stage.py, or config_prod.py")
    console.print("  2. Set DRY_RUN = True or False")
    console.print("  3. Restart the bot (main.py)")
    console.print("\nAlternatively, use: export BOT_ENV=prod (sets DRY_RUN=False)")


def main():
    parser = argparse.ArgumentParser(
        prog="poly-cli",
        description="Polymarket 15m BTC Bot CLI",
    )
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("validate", help="Validate runtime configuration")
    sub.add_parser("scan-once", help="Run a single market scan (DRY_RUN expected)")
    sub.add_parser("run-tests", help="Run test suite (pytest)")

    # Database commands
    db_stats = sub.add_parser("db-stats", help="Show trade statistics from database")
    db_stats.add_argument("--days", type=int, default=1, help="Days to query (default: 1)")

    db_backup = sub.add_parser("db-backup", help="Backup trade database")
    db_backup.add_argument(
        "--reset", action="store_true", help="Reset DB after backup"
    )

    # Log commands
    log_rot = sub.add_parser("log-rotate", help="Backup and rotate log file")
    log_rot.add_argument(
        "--reset", action="store_true", help="Reset log after backup"
    )

    # Misc
    sub.add_parser("toggle-dry-run", help="Instructions to toggle DRY_RUN mode")

    args = parser.parse_args()
    if args.cmd == "validate":
        cmd_validate(args)
    elif args.cmd == "scan-once":
        cmd_scan_once(args)
    elif args.cmd == "run-tests":
        cmd_run_tests(args)
    elif args.cmd == "db-stats":
        cmd_db_stats(args)
    elif args.cmd == "db-backup":
        cmd_db_backup(args)
    elif args.cmd == "log-rotate":
        cmd_log_rotate(args)
    elif args.cmd == "toggle-dry-run":
        cmd_toggle_dry_run(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
