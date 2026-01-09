
import strategies.crowd_follower as cf


def make_market(volume=10000):
    return {"volume": str(volume), "question": "Q", "slug": "s-0"}


def test_vig_out_of_range(monkeypatch):
    # Vig too high -> skip
    monkeypatch.setattr(
        cf, "get_token_prices", lambda client, market: (0.6, 0.6, "y", "n")
    )
    strat = cf.CrowdFollowerStrategy(client=None)
    status = strat.scan_and_get_status(make_market())
    assert status[3] is None


def test_no_candidates(monkeypatch):
    # Both sides outside valid range -> no action
    # With adaptive vig tolerance, volume 10000 uses tight range (0.98, 1.02)
    # Prices 0.15, 0.85 -> vig=1.0 (valid)
    # But 0.15 is below MIN_THRESHOLD [0.30, 0.90], so only 0.85 qualifies
    # Actually 0.85 IS in range, so this will trigger. Let's use out-of-range prices
    # Prices 0.1, 0.9 -> vig=1.0 but 0.9 is at MAX_THRESHOLD boundary
    # Better: use prices outside the price range entirely
    monkeypatch.setattr(
        cf, "get_token_prices", lambda client, market: (0.05, 0.95, "y", "n")
    )
    strat = cf.CrowdFollowerStrategy(client=None)
    status = strat.scan_and_get_status(make_market())
    # Neither 0.05 nor 0.95 are in [0.30, 0.90] range for dev config
    assert status[3] is None


def test_buy_strongest_and_token(monkeypatch):
    called = {}

    def fake_buy(client, token_id, amount, side_name, market=None, price=None):
        called["token"] = token_id
        called["side"] = side_name
        called["price"] = price
        return True

    # Yes is stronger, both in valid range
    # With high volume (10000), uses tight vig range (0.98, 1.02)
    # Prices: yes=0.55, no=0.45 -> vig=1.0 (valid)
    # Both are in range [0.30, 0.90] for dev config
    monkeypatch.setattr(
        cf, "get_token_prices", lambda client, market: (0.55, 0.45, "ytoken", "ntoken")
    )
    monkeypatch.setattr(cf, "execute_market_buy", fake_buy)

    strat = cf.CrowdFollowerStrategy(client=None)
    market = make_market()
    prices, vig, vol, edge_msg, edge_details = strat.scan_for_edge(market)
    assert edge_msg is not None
    assert edge_details is not None
    assert edge_details["side"] == "yes"
    assert edge_details["token_id"] == "ytoken"
    # Execute to verify behavior
    strat.execute_edge(edge_details, market)
    assert called["side"] == "yes"
    assert called["token"] == "ytoken"


def test_tie_prefers_configured_side(monkeypatch):
    called = {}

    def fake_buy(client, token_id, amount, side_name, market=None, price=None):
        called["token"] = token_id
        called["side"] = side_name
        return True

    # Tie prices: 0.5 each -> vig=1.0 (valid for high volume)
    monkeypatch.setattr(
        cf, "get_token_prices", lambda client, market: (0.5, 0.5, "yt", "nt")
    )
    monkeypatch.setattr(cf, "execute_market_buy", fake_buy)

    strat = cf.CrowdFollowerStrategy(client=None)
    market = make_market()
    # default PREFERRED_SIDE is 'yes', should pick yes on tie
    prices, vig, vol, edge_msg, edge_details = strat.scan_for_edge(market)
    assert edge_msg is not None
    assert edge_details is not None
    assert edge_details["side"] == "yes"
    strat.execute_edge(edge_details, market)
    assert called["side"] == "yes"

    # Flip preference and ensure it picks 'no' on tie
    strat.config.PREFERRED_SIDE = "no"
    called.clear()
    prices, vig, vol, edge_msg, edge_details = strat.scan_for_edge(market)
    assert edge_msg is not None
    assert edge_details is not None
    assert edge_details["side"] == "no"
    strat.execute_edge(edge_details, market)
    assert called["side"] == "no"
