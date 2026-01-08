from types import SimpleNamespace

from pricing import _mid_from_book


def make_book(bid_price, ask_price):
    bid = SimpleNamespace(price=bid_price)
    ask = SimpleNamespace(price=ask_price)
    return SimpleNamespace(bids=[bid], asks=[ask])


def test_mid_from_book():
    book = make_book(0.3, 0.7)
    m = _mid_from_book(book)
    assert abs(m - 0.5) < 1e-9

    # Missing data falls back to 0.5
    book2 = SimpleNamespace(bids=[], asks=[])
    assert _mid_from_book(book2) == 0.5
