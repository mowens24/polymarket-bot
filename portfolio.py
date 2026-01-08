# portfolio.py - Simulated positions and P&L for paper trade (dry run)

from typing import Dict, List, Tuple

from logger import log_info


class PaperPortfolio:
    def __init__(self) -> None:
        self.positions: List[Dict] = []

    def add_position(
        self, market: Dict, side: str, amount: float, price: float
    ) -> None:
        shares = amount / price
        pos = {
            "market": market.get("question", "Unknown"),
            "side": side,
            "shares": shares,
            "avg_price": price,
            "current_value": amount,
            "pnl": 0.0,
        }
        self.positions.append(pos)
        log_info(f"PAPER BUY: {shares:.2f} shares of {side.upper()} @ ${price:.4f}")
        log_info(f"Market: {pos['market']}")

    def update_pnl(
        self, market: Dict, prices: Tuple[float, float]
    ) -> Tuple[int, float]:
        up, down = prices
        market_question = market.get("question", "Unknown")
        for pos in self.positions:
            if pos["market"] == market_question:
                if pos["side"] == "yes":
                    pos["current_value"] = pos["shares"] * up
                else:
                    pos["current_value"] = pos["shares"] * down
                pos["pnl"] = pos["current_value"] - pos["shares"] * pos["avg_price"]

        total_pnl = sum(pos["pnl"] for pos in self.positions)
        return len(self.positions), total_pnl

    def close_slot(self, market_question: str) -> None:
        self.positions = [p for p in self.positions if p["market"] != market_question]
        log_info("Paper positions closed for ended slot")
