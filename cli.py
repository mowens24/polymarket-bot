#!/usr/bin/env python3
"""Simple CLI for runtime checks and dry-run scans."""

import argparse
import subprocess

from logger import console


def cmd_validate(args):
    from config import validate_config

    errors = validate_config()
    if errors:
        for e in errors:
            console.print(f"[bold red]CONFIG ERROR:[/bold red] {e}")
        raise SystemExit(1)
    console.print("[bold green]Config OK[/bold green]")


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


def main():
    parser = argparse.ArgumentParser(prog="poly-cli")
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("validate", help="Validate runtime configuration")
    sub.add_parser("scan-once", help="Run a single market scan (DRY_RUN expected)")
    sub.add_parser("run-tests", help="Run test suite (pytest)")

    args = parser.parse_args()
    if args.cmd == "validate":
        cmd_validate(args)
    elif args.cmd == "scan-once":
        cmd_scan_once(args)
    elif args.cmd == "run-tests":
        cmd_run_tests(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
