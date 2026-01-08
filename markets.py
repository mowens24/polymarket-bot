# markets.py - Aware timezones for correct EST alignment, switches on boundary

import datetime
from datetime import timezone

import requests

from config import MIN_VOLUME
from logger import log_error, log_info

GAMMA_MARKETS_API = "https://gamma-api.polymarket.com/markets"

current_slot_unix = None  # Global to track current slot


def get_current_slot_unix():
    global current_slot_unix

    utc_now = datetime.datetime.now(timezone.utc)

    # EST = UTC-5
    est_tz = timezone(-datetime.timedelta(hours=5))

    est_now = utc_now.astimezone(est_tz)

    # Floor to nearest 15min boundary in EST
    minutes_floored = (est_now.minute // 15) * 15
    est_slot_start = est_now.replace(minute=minutes_floored, second=0, microsecond=0)

    # Unix of slot start (UTC timestamp)
    utc_slot_start = est_slot_start.astimezone(timezone.utc)
    slot_unix = int(utc_slot_start.timestamp())

    # Detect boundary cross
    if current_slot_unix != slot_unix:
        if current_slot_unix is not None:
            log_info("*** NEW 15M SLOT STARTED *** Switching market")
        current_slot_unix = slot_unix
        log_info(
            f"Current EST slot start: {est_slot_start.strftime('%I:%M %p EST')} (unix {slot_unix})"
        )

    return slot_unix


def fetch_current_15min_btc_market():
    slot_unix = get_current_slot_unix()
    slug = f"btc-updown-15m-{slot_unix}"

    params = {"slug": slug}
    try:
        response = requests.get(GAMMA_MARKETS_API, params=params)
        response.raise_for_status()
        markets = response.json()

        if not markets:
            log_info(f"No market for slug {slug} yet - new slot, retry next scan")
            return None

        market = markets[0]
        vol = float(market.get("volume", 0))
        question = market.get("question", "Unknown")
        log_info(f"ACTIVE SLOT: {question} (Vol ${vol:.2f})")
        if vol < MIN_VOLUME:
            log_info(f"Low volume (${vol:.2f}) - waiting for liquidity")
            # Optional: return None to skip

        return market

    except Exception as e:
        log_error(f"Fetch failed for {slug}: {e}")
        return None
