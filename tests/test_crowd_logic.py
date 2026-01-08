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
    # Both sides below MIN_THRESHOLD -> no action
    monkeypatch.setattr(
        cf, "get_token_prices", lambda client, market: (0.5, 0.5, "y", "n")
    )
    strat = cf.CrowdFollowerStrategy(client=None)
    status = strat.scan_and_get_status(make_market())
    assert status[3] is None


def test_buy_strongest_and_token(monkeypatch):
    called = {}

    def fake_buy(client, token_id, amount, side_name, market=None, price=None):
        called["token"] = token_id
        called["side"] = side_name
        called["price"] = price
        return True

    # Yes is stronger
    monkeypatch.setattr(
        cf, "get_token_prices", lambda client, market: (0.85, 0.2, "ytoken", "ntoken")
    )
    monkeypatch.setattr(cf, "execute_market_buy", fake_buy)

    strat = cf.CrowdFollowerStrategy(client=None)
    status = strat.scan_and_get_status(make_market())
    assert status[3] is not None
    assert called["side"] == "yes"
    assert called["token"] == "ytoken"


def test_tie_prefers_configured_side(monkeypatch):
    called = {}

    def fake_buy(client, token_id, amount, side_name, market=None, price=None):
        called["token"] = token_id
        called["side"] = side_name
        return True

    # Tie prices
    monkeypatch.setattr(
        cf, "get_token_prices", lambda client, market: (0.8, 0.8, "yt", "nt")
    )
    monkeypatch.setattr(cf, "execute_market_buy", fake_buy)

    strat = cf.CrowdFollowerStrategy(client=None)
    # Relax vig and threshold checks so tie logic is exercised in test
    strat.config.VIG_TOLERANCE_LOW = 0.0
    strat.config.VIG_TOLERANCE_HIGH = 2.0
    strat.config.MIN_THRESHOLD = 0.0

    # default PREFERRED_SIDE is 'yes', should pick yes on tie
    status = strat.scan_and_get_status(make_market())
    assert status[3] is not None
    assert called["side"] == "yes"

    # Flip preference and ensure it picks 'no' on tie
    strat.config.PREFERRED_SIDE = "no"
    called.clear()
    status = strat.scan_and_get_status(make_market())
    assert status[3] is not None
    assert called["side"] == "no"
