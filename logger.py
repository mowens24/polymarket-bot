# logger.py - Fancy Rich CLI

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
    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh.setFormatter(formatter)
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


# For fancy status panel
def get_status_panel(
    market: Optional[dict] = None,
    prices: Tuple[float, float] = (0.5, 0.5),
    vig: float = 1.0,
    vol: float = 0.0,
    edge: Optional[str] = None,
    time_left: int = 0,
    total_time: int = 900,
) -> Panel:
    table = Table(box=box.ROUNDED, show_header=False, padding=1, expand=True)

    if market:
        question = market.get("question", "Unknown")
        table.add_row("[bold magenta]Market[/bold magenta]", question)
        table.add_row("[bold yellow]Volume[/bold yellow]", f"${vol:,.2f}")
        up, down = prices
        table.add_row("[bold green]Up (Yes)[/bold green]", f"${up:.4f}")
        table.add_row("[bold red]Down (No)[/bold red]", f"${down:.4f}")
        table.add_row("[bold cyan]Vig[/bold cyan]", f"{vig:.3f}")

        if edge:
            table.add_row("[bold bright_green]EDGE[/bold bright_green]", edge)

        # Time left in slot progress bar (reuse a single Progress instance)
        global _slot_task_id
        if _slot_task_id is None:
            _slot_task_id = slot_progress.add_task(
                "slot", total=total_time, completed=total_time - time_left
            )
        else:
            slot_progress.update(
                _slot_task_id, total=total_time, completed=total_time - time_left
            )

        table.add_row(slot_progress)
    else:
        table.add_row(
            "[bold red]Status[/bold red]", "No active slot - waiting for next..."
        )

    mode = "DRY RUN" if DRY_RUN else "[bold red]LIVE TRADING[/bold red]"
    title = f"[bold blue]Polymarket 15m BTC Bot[/bold blue] | {mode}"

    return Panel(
        table, title=title, subtitle="[dim]Crowd-following lopsides • Live update[/dim]"
    )
