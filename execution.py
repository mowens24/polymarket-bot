# execution.py

from typing import Optional

# Use tenacity for robust retries
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
)

from config import DRY_RUN
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


def execute_market_buy(
    client,
    token_id: str,
    amount_usd: float,
    side_name: str,
    market: Optional[dict] = None,
    price: Optional[float] = None,
) -> bool:
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
        log_trade(
            f"SUCCESS: Bought {side_name.upper()} ${amount_usd:.2f} | Tx: {tx_hash}"
        )
        return True
    except Exception as e:
        log_error(f"Trade failed after retries ({side_name}): {e}")
        return False
