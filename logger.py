# logger.py - Fancy Rich CLI with structured JSON logging

import json
import logging
import os
from typing import Optional, Tuple

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TextColumn, TimeRemainingColumn
from rich.table import Table

from config import DRY_RUN  # Import DRY_RUN here

console = Console()

# Also configure a standard library logger to capture logs to a file for diagnostics
LOG_FILE = os.path.join(os.path.dirname(__file__), "bot.log")
_std_logger = logging.getLogger("polybot")
if not _std_logger.handlers:
    _std_logger.setLevel(logging.INFO)
    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(logging.INFO)

    # JSON formatter for structured logging
    class JSONFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            log_obj = {
                "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S"),
                "level": record.levelname,
                "message": record.getMessage(),
            }
            return json.dumps(log_obj)

    fh.setFormatter(JSONFormatter())
    _std_logger.addHandler(fh)

# Reusable progress bar for time-left display to avoid recreating each render
slot_progress = Progress(
    TextColumn("[bold cyan]Time left in slot:[/bold cyan]"),
    BarColumn(),
    TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    TimeRemainingColumn(),
    expand=True,
)
_slot_task_id = None


def log_info(message: str) -> None:
    console.print(f"[bold cyan][INFO][/bold cyan] {message}")
    _std_logger.info(message)


def log_trade(message: str) -> None:
    console.print(f"[bold green]✅ TRADE[/bold green] {message}")
    _std_logger.info(f"TRADE: {message}")


def log_error(message: str) -> None:
    console.print(f"[bold red]❌ ERROR[/bold red] {message}")
    _std_logger.error(message)


def _sparkline(value: float, max_val: float = 100.0, width: int = 10) -> str:
    """Generate a simple sparkline bar."""
    if max_val == 0:
        return "░" * width
    filled = int((value / max_val) * width)
    filled = min(filled, width)
    return "█" * filled + "░" * (width - filled)


# For fancy status panel
def get_status_panel(
    market: Optional[dict] = None,
    prices: Tuple[float, float] = (0.5, 0.5),
    vig: float = 1.0,
    vol: float = 0.0,
    edge: Optional[str] = None,
    time_left: int = 0,
    total_time: int = 900,
    position_status: Optional[dict] = None,
    metrics: Optional[dict] = None,
) -> Panel:
    """Return a two-column status panel: market info (left) and metrics/positions (right)."""

    left = Table(box=box.SIMPLE_HEAVY, show_header=False, padding=(0, 1))
    right = Table(box=box.SIMPLE_HEAVY, show_header=False, padding=(0, 1))

    if market:
        question = market.get("question", "Unknown")
        left.add_row("[bold magenta]Market[/bold magenta]", question[:60])
        left.add_row("[bold yellow]Volume[/bold yellow]", f"${vol:,.2f}")
        up, down = prices

        # Color code prices: green for high, red for low
        up_color = "green" if up > 0.5 else "red"
        down_color = "red" if down > 0.5 else "green"
        left.add_row(f"[bold {up_color}]Up (Yes)[/bold {up_color}]", f"{up:.4f}")
        left.add_row(f"[bold {down_color}]Down (No)[/bold {down_color}]", f"{down:.4f}")

        # Vig with color: tight range is good (green), loose is risky (yellow)
        vig_color = "green" if 0.98 <= vig <= 1.02 else "yellow"
        left.add_row(f"[bold {vig_color}]Vig[/bold {vig_color}]", f"{vig:.3f}")

        if edge:
            left.add_row("[bold bright_green]🔥 EDGE[/bold bright_green]", edge)

        # Time left progress (single shared Progress)
        global _slot_task_id
        if _slot_task_id is None:
            _slot_task_id = slot_progress.add_task(
                "slot", total=total_time, completed=total_time - time_left
            )
        else:
            slot_progress.update(
                _slot_task_id, total=total_time, completed=total_time - time_left
            )
        left.add_row("", slot_progress)
    else:
        left.add_row("[bold red]Status[/bold red]", "No active slot - waiting...")

    # Right column: metrics and positions with sparklines
    if metrics:
        right.add_row("[bold cyan]📊 Metrics[/bold cyan]", "")
        trades = metrics.get("total_trades", 0)
        right.add_row("Total Trades", str(trades))

        daily_loss = metrics.get("daily_loss_usd", 0.0)
        loss_color = "red" if daily_loss > 50 else "yellow" if daily_loss > 20 else "green"
        right.add_row("Daily Loss", f"[{loss_color}]${daily_loss:.2f}[/{loss_color}]")

        loss_streak = metrics.get("current_loss_streak", 0)
        streak_color = "red" if loss_streak >= 3 else "yellow" if loss_streak > 0 else "green"
        right.add_row("Loss Streak", f"[{streak_color}]{'🔴' * loss_streak or '✅'}[/{streak_color}]")
    else:
        right.add_row("[bold cyan]📊 Metrics[/bold cyan]", "Loading...")

    if position_status:
        right.add_row("[bold magenta]📍 Positions[/bold magenta]", "")
        active = position_status.get("active_positions", 0)
        right.add_row("Active", str(active))

        exposure = position_status.get("total_exposure_usd", 0.0)
        spark = _sparkline(exposure, max_val=100.0, width=10)
        right.add_row("Exposure", f"{spark} ${exposure:.2f}")

        daily_trades = position_status.get("daily_trades", 0)
        right.add_row("Daily Trades", str(daily_trades))
    else:
        right.add_row("[bold magenta]📍 Positions[/bold magenta]", "Loading...")
        right.add_row("[bold magenta]📍 Positions[/bold magenta]", "Loading...")

    # Assemble main table with two columns
    main = Table.grid(expand=True)
    main.add_column(ratio=2)
    main.add_column(ratio=1)
    main.add_row(left, right)

    mode = "🟢 DRY RUN" if DRY_RUN else "[bold red]🔴 LIVE[/bold red]"
    title = f"[bold blue]Polymarket 15m BTC Bot[/bold blue] | {mode}"

    return Panel(
        main,
        title=title,
        subtitle="[dim]Crowd-following lopsides • Live update[/dim]",
        border_style="blue",
    )


def get_pnl_panel(position_monitor) -> Panel:  # type: ignore[name-defined]
    """Display live P&L on open positions and recent closed positions."""

    # Open positions section
    open_table = Table(
        title="[bold cyan]📈 OPEN POSITIONS[/bold cyan]",
        box=box.ROUNDED,
        expand=False,
    )
    open_table.add_column("Market", style="cyan", width=20)
    open_table.add_column("Side", width=6)
    open_table.add_column("Shares", justify="right", width=10)
    open_table.add_column("Entry $", justify="right", width=10)
    open_table.add_column("Current $", justify="right", width=10)
    open_table.add_column("P&L", justify="right", width=12)
    open_table.add_column("Return %", justify="right", width=10)

    positions = position_monitor.get_all_positions()
    if positions:
        for pos in positions:
            # Fetch current price from latest market data if available
            # For now, just show entry price; will update when price fetched
            entry_price = pos.get("entry_price", 0)
            current_price = pos.get("current_price", entry_price)
            side = pos.get("side", "?")
            shares = pos.get("shares", 0)

            # Calculate P&L based on current price
            if side == "yes":
                pnl = (current_price - entry_price) * shares
            else:
                pnl = (entry_price - current_price) * shares

            pct = ((pnl / (entry_price * shares)) * 100) if entry_price > 0 else 0
            color = "green" if pnl >= 0 else "red"

            open_table.add_row(
                pos.get("market_name", "Unknown"),
                f"[cyan]{side}[/cyan]",
                f"{shares:.2f}",
                f"${entry_price:.4f}",
                f"${current_price:.4f}",
                f"[{color}]${pnl:.2f}[/{color}]",
                f"[{color}]{pct:+.1f}%[/{color}]",
            )
    else:
        open_table.add_row("[dim]No open positions[/dim]", "", "", "", "", "", "")

    # Closed positions section (last 5)
    closed_table = Table(
        title="[bold yellow]📊 CLOSED POSITIONS (Recent)[/bold yellow]",
        box=box.ROUNDED,
        expand=False,
    )
    closed_table.add_column("Market", style="yellow", width=20)
    closed_table.add_column("Side", width=6)
    closed_table.add_column("Entry $", justify="right", width=10)
    closed_table.add_column("Exit $", justify="right", width=10)
    closed_table.add_column("Realized P&L", justify="right", width=14)
    closed_table.add_column("Return %", justify="right", width=10)

    summary = position_monitor.get_summary()
    closed_list = summary.get("closed_position_list", [])

    if closed_list:
        for pos in reversed(closed_list[-5:]):  # Show last 5 in reverse (newest first)
            pnl = pos.get("realized_pnl", 0)
            pct = pos.get("realized_pct", 0)
            color = "green" if pnl >= 0 else "red"

            closed_table.add_row(
                pos.get("market_id", "Unknown"),
                pos.get("side", "?"),
                f"${pos.get('entry_price', 0):.4f}",
                f"${pos.get('exit_price', 0):.4f}",
                f"[{color}]${pnl:.2f}[/{color}]",
                f"[{color}]{pct:+.1f}%[/{color}]",
            )
    else:
        closed_table.add_row("[dim]No closed positions[/dim]", "", "", "", "", "")

    # Summary stats
    stats = Table(box=box.SIMPLE, expand=False)
    stats.add_column("Metric", style="dim")
    stats.add_column("Value", justify="right", style="bold cyan")

    total_realized = summary.get("total_realized_pnl", 0)
    color = "green" if total_realized >= 0 else "red"
    stats.add_row("Total Realized P&L", f"[{color}]${total_realized:.2f}[/{color}]")
    stats.add_row("Open Positions", str(summary.get("open_positions", 0)))
    stats.add_row("Closed Positions", str(summary.get("closed_positions", 0)))

    # Combine tables
    content = Table.grid(expand=True)
    content.add_row(open_table)
    content.add_row(closed_table)
    content.add_row(stats)

    return Panel(
        content,
        title="[bold magenta]💰 REAL-TIME P&L MONITOR[/bold magenta]",
        border_style="magenta",
    )
