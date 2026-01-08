# pricing.py - Use Gamma for real odds, fallback to book

import json
from typing import Optional, Tuple

from logger import log_error, log_info


def _mid_from_book(book) -> float:
    try:
        if book.bids and book.asks and len(book.bids) > 0 and len(book.asks) > 0:
            bid = float(book.bids[0].price)
            ask = float(book.asks[0].price)
            return (bid + ask) / 2
    except Exception as e:
        log_error(f"Mid calc error: {e}")
    return 0.5


def get_token_prices(
    client, market
) -> Tuple[float, float, Optional[str], Optional[str]]:
    clob_str = market.get("clobTokenIds", "[]")
    try:
        clob_ids = json.loads(clob_str)
    except Exception as e:
        log_error(f"clobTokenIds parse fail: {e}")
        return 0.5, 0.5, None, None

    if len(clob_ids) != 2:
        log_error(f"Bad clob count: {clob_ids}")
        return 0.5, 0.5, None, None

    yes_token = clob_ids[0]
    no_token = clob_ids[1]

    # Primary: Gamma outcomePrices (real tradable odds)
    prices_str = market.get("outcomePrices", "[]")
    try:
        op = json.loads(prices_str)
        if len(op) == 2:
            yes_price = float(op[0])
            no_price = float(op[1])
            log_info(f"Using Gamma prices: Yes ${yes_price:.4f} | No ${no_price:.4f}")
            vig = yes_price + no_price
            log_info(f"Vig sum: {vig:.3f}")
            return yes_price, no_price, yes_token, no_token
    except Exception as e:
        log_info(f"Gamma fail ({e}) - book fallback")

    # Fallback to book
    try:
        yes_book = client.get_order_book(yes_token)
        no_book = client.get_order_book(no_token)
        yes_price = _mid_from_book(yes_book)
        no_price = _mid_from_book(no_book)
        log_info(f"CLOB book mid: Yes ${yes_price:.4f} | No ${no_price:.4f}")
    except Exception as e:
        log_error(f"Book failed: {e}")
        yes_price, no_price = 0.5, 0.5

    vig = yes_price + no_price
    log_info(f"Vig sum: {vig:.3f}")

    return yes_price, no_price, yes_token, no_token
