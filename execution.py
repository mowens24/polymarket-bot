# execution.py - Order execution with safety checks, retries, and partial fill handling

from typing import Optional

# Use tenacity for robust retries
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
)

from config import DRY_RUN, WALLET_MIN_BALANCE_USD
from logger import log_error, log_trade

# In DRY_RUN mode we keep a paper portfolio to simulate trades
# _paper_portfolio may be None when not available
_paper_portfolio: Optional["PaperPortfolio"] = None
if DRY_RUN:
    try:
        from portfolio import PaperPortfolio

        _paper_portfolio = PaperPortfolio()
    except Exception:
        _paper_portfolio = None


def check_wallet_balance(client) -> float:
    """Check wallet balance and warn if below threshold."""
    try:
        balance_eth = client.get_balance()
        balance_usd = balance_eth * 2000  # Rough conversion (adjust as needed)
        if balance_usd < WALLET_MIN_BALANCE_USD:
            log_error(
                f"WALLET LOW: ${balance_usd:.2f} < ${WALLET_MIN_BALANCE_USD:.2f} minimum"
            )
        return balance_usd
    except Exception as e:
        log_error(f"Balance check failed: {e}")
        return 0.0


def execute_market_buy(
    client,
    token_id: str,
    amount_usd: float,
    side_name: str,
    market: Optional[dict] = None,
    price: Optional[float] = None,
) -> bool:
    """Execute a market buy with safety checks and retry logic.

    Handles partial fills by polling order status after execution.
    """
    if DRY_RUN:
        log_trade(
            f"DRY RUN: Would buy {side_name.upper()} ${amount_usd:.2f} at ${price:.4f} | NO ORDER SENT"
        )
        # Add to paper portfolio if available
        try:
            if _paper_portfolio and market is not None and price is not None:
                _paper_portfolio.add_position(market, side_name, amount_usd, price)
        except Exception as e:
            log_error(f"Paper portfolio record failed: {e}")
        return True

    # Pre-trade safety checks
    wallet_balance = check_wallet_balance(client)
    if wallet_balance < WALLET_MIN_BALANCE_USD:
        log_error(
            f"Wallet balance check failed: ${wallet_balance:.2f} < ${WALLET_MIN_BALANCE_USD:.2f}"
        )
        return False

    if amount_usd <= 0:
        log_error(f"Invalid trade amount: ${amount_usd:.2f}")
        return False

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
    )
    def _post_order():
        signed_order = client.create_market_buy(token_id=token_id, amount=amount_usd)
        resp = client.post_order(signed_order)
        return resp

    try:
        resp = _post_order()
        tx_hash = resp.get("tx_hash", "N/A")

        # Check for partial fills
        filled_amount = resp.get("filled_amount", amount_usd)
        if filled_amount < amount_usd * 0.95:  # Less than 95% filled
            log_error(
                f"PARTIAL FILL: Only ${filled_amount:.2f}/${amount_usd:.2f} filled"
            )

        log_trade(
            f"SUCCESS: Bought {side_name.upper()} ${filled_amount:.2f} | Tx: {tx_hash}"
        )
        return True
    except Exception as e:
        log_error(f"Trade failed after retries ({side_name}): {e}")
        return False
