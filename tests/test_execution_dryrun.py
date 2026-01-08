from execution import _paper_portfolio, execute_market_buy


def test_dry_run_records_paper_portfolio():
    # Ensure DRY_RUN mode is active (config.DRY_RUN defaults to True in this repo)
    assert _paper_portfolio is not None

    # Clear any existing positions
    _paper_portfolio.positions.clear()

    dummy_market = {"question": "DryRun Market"}
    res = execute_market_buy(
        client=None,
        token_id="y",
        amount_usd=1.0,
        side_name="yes",
        market=dummy_market,
        price=0.8,
    )
    assert res is True
    assert len(_paper_portfolio.positions) == 1
    pos = _paper_portfolio.positions[0]
    assert pos["market"] == "DryRun Market"
    assert pos["side"] == "yes"
