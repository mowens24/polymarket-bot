# client.py - ClobClient wrapper

import os

from dotenv import load_dotenv
from eth_account import Account
from py_clob_client.client import ClobClient

load_dotenv()

private_key = os.getenv("POLYGON_PRIVATE_KEY")
if not private_key:
    raise ValueError("POLYGON_PRIVATE_KEY not set in .env")

wallet_address = Account.from_key(private_key).address


def get_client():
    """Initialize and return a ClobClient with API credentials."""
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=private_key,
        chain_id=137,
        signature_type=1,
        funder=wallet_address,
    )
    client.set_api_creds(client.create_or_derive_api_creds())
    _attach_balance_helper(client)
    return client


def _get_balance_direct(client) -> float:
    """Try direct get_balance() call."""
    try:
        if hasattr(client, "get_balance"):
            return float(client.get_balance())
    except Exception:
        pass
    return -1.0


def _get_balance_wallet(client) -> float:
    """Try wallet nested object."""
    try:
        wallet = getattr(client, "wallet", None)
        if wallet:
            for name in ("get_balance", "balance", "get_wallet_balance"):
                fn = getattr(wallet, name, None)
                if callable(fn):
                    return float(fn())
    except Exception:
        pass
    return -1.0


def _get_balance_provider(client) -> float:
    """Try provider-style call."""
    try:
        provider = getattr(client, "provider", None)
        addr = getattr(client, "address", None) or getattr(
            client, "wallet_address", None
        )
        if not addr:
            addr = wallet_address
        if provider:
            fn = getattr(provider, "get_balance", None)
            if callable(fn):
                return float(fn(addr))
    except Exception:
        pass
    return -1.0


def _attach_balance_helper(client) -> None:
    """Attach a resilient get_balance method to the client."""

    def get_balance_safe() -> float:
        """Resilient wrapper trying multiple balance APIs."""
        # Try direct method first
        val = _get_balance_direct(client)
        if val >= 0:
            return val

        # Try wallet object
        val = _get_balance_wallet(client)
        if val >= 0:
            return val

        # Try provider
        val = _get_balance_provider(client)
        if val >= 0:
            return val

        # No API found
        from logger import log_error

        log_error("Balance check failed: no supported API found on ClobClient")
        return 0.0

    client.get_balance = get_balance_safe  # type: ignore[attr-defined]
