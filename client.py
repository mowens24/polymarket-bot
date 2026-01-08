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
    client = ClobClient(
        host="https://clob.polymarket.com",
        key=private_key,
        chain_id=137,
        signature_type=1,
        funder=wallet_address,
    )
    client.set_api_creds(client.create_or_derive_api_creds())
    # Return the client instance. `wallet_address` is available at module scope if needed.
    return client
