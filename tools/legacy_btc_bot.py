import json
import os
import time

import requests
from anthropic import Anthropic
from dotenv import load_dotenv
from eth_account import Account
from py_clob_client.client import ClobClient

load_dotenv()

# Setup
anthropic = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
private_key = os.getenv("POLYGON_PRIVATE_KEY")
host = "https://clob.polymarket.com"
chain_id = 137  # Polygon

# Get your wallet address from private key (funder for normal wallets)
wallet_address = Account.from_key(private_key).address

# Initialize client - signature_type=1 for normal MetaMask/EOA wallets
# Use signature_type=1 if email/Magic/proxy wallet
client = ClobClient(
    host=host,
    key=private_key,
    chain_id=chain_id,
    signature_type=1,  # Change to 1 if using Polymarket proxy wallet
    funder=wallet_address,
)

# Always set creds (creates if new, derives if exists)
client.set_api_creds(client.create_or_derive_api_creds())

print("CLOB ready - authenticated")


def fetch_15min_btc_markets():
    params = {"active": "true", "closed": "false", "limit": "200"}
    response = client.signed_request("GET", "/markets", params=params)
    markets = response.json()
    targets = []
    for m in markets:
        q = m["question"].lower()
        if "bitcoin up or down" in q and ("15" in q or "pm-" in q or "am-" in q):
            if float(m.get("volume", 0)) > 20000:  # Min liquidity
                targets.append(m)
    return sorted(targets, key=lambda x: x.get("end_date", ""))  # Soonest first


def get_live_btc_price():
    try:
        return requests.get(
            "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        ).json()["price"]
    except Exception:
        return "unknown"


def claude_decide(market, live_price):
    prompt = f"""
    15-Min BTC Up/Down Market: {market["question"]}
    Current YES (Up) odds: {float(market["prices"][0]) * 100:.1f}% (price ${market["prices"][0]})
    NO (Down) odds: {float(market["prices"][1]) * 100:.1f}%
    Volume: ${int(market["volume"]):,}
    Live BTC price: ${live_price}
    Time to resolution: soon (15-min market)

    Short-term momentum analysis only. Is Up or Down mispriced?
    Output ONLY JSON:
    {{
      "decision": "buy_yes" | "buy_no" | "none",
      "amount_usd": 20,  // Suggest 10-50 USD
      "reason": "short explanation"
    }}
    """
    try:
        message = anthropic.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        # Safely extract text from the response (Anthropic types vary)
        from typing import Any, cast

        block = message.content[0]
        block_any = cast("Any", block)

        text_val = getattr(block_any, "text", None)
        if text_val is None:
            # If it's dict-like, use get(); using cast(Any, ...) suppresses mypy union-attr
            try:
                text_val = block_any.get("text", "")
            except Exception:
                text_val = str(block_any)

        return json.loads(str(text_val).strip())
    except Exception as e:
        print("Claude parse error:", e)
        return {"decision": "none", "reason": "parse fail"}


# Main Loop
print("Bot starting - scanning every 2 minutes...")
while True:
    markets = fetch_15min_btc_markets()
    live_price = get_live_btc_price()

    if not markets:
        print(f"{time.strftime('%H:%M')} - No active 15-min BTC markets found.")
    else:
        print(f"{time.strftime('%H:%M')} - Found {len(markets)} 15-min markets")
        for market in markets[:5]:  # Top 5 soonest
            decision = claude_decide(market, live_price)
            print(f"\nMarket: {market['question'][:70]}...")
            print(f"Odds: {float(market['prices'][0]) * 100:.1f}% Up")
            d = decision.get("decision", "none")
            amt = decision.get("amount_usd", 0)
            reason = decision.get("reason", "")
            print(f"Claude: {d} ${amt} - {reason}")

            if decision.get("decision") == "none":
                continue

            # Safety: max $5 per trade
            amount_usd = min(decision.get("amount_usd", 1), 5)

            side_yes = "yes" in decision["decision"]
            token_id = market["tokens"][0 if side_yes else 1]["token_id"]

            try:
                # Simple market buy for exact $ amount
                signed_order = client.create_market_buy(
                    token_id=token_id, amount=amount_usd
                )
                resp = client.post_order(signed_order)
                print(
                    f"SUCCESS: TRADED {decision['decision'].upper()} ${amount_usd} | Tx: {resp.get('tx_hash', 'N/A')}"
                )
            except Exception as e:
                print(f"Trade failed: {e}")

    time.sleep(120)  # Every 2 minutes
