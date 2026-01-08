from strategies.crowd_follower import CrowdFollowerStrategy


class DummyClient:
    pass


def make_market(volume, yes_price=0.8, no_price=0.2):
    return {
        "question": "Test market",
        "clobTokenIds": '["y","n"]',
        "outcomePrices": f"[{yes_price},{no_price}]",
        "volume": str(volume),
        "slug": "test-0",
    }


def test_skip_low_volume(monkeypatch):
    client = DummyClient()
    strat = CrowdFollowerStrategy(client)
    market = make_market(volume=10)  # default MIN_VOLUME is larger
    status = strat.scan_and_get_status(market)
    # Expect no edge due to low volume
    assert status[3] is None
