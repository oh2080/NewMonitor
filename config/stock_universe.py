"""股票池管理"""
from dataclasses import dataclass, field
from typing import Optional

from .settings import get_settings


@dataclass
class StockInfo:
    symbol: str
    name: str
    market: str  # us_semi, cn_semi, cn_ai


class StockUniverse:
    """股票池"""

    def __init__(self):
        settings = get_settings()
        raw = settings.stock_universe_raw
        self._stocks: dict[str, StockInfo] = {}
        for market, items in raw.items():
            for item in items:
                info = StockInfo(
                    symbol=item["symbol"],
                    name=item["name"],
                    market=market,
                )
                self._stocks[item["symbol"]] = info

    def get_by_market(self, market: str) -> list[StockInfo]:
        return [s for s in self._stocks.values() if s.market == market]

    def get_cn_stocks(self) -> list[StockInfo]:
        """获取所有A股（cn_semi + cn_ai）"""
        return [s for s in self._stocks.values() if s.market.startswith("cn_")]

    def get_us_stocks(self) -> list[StockInfo]:
        return self.get_by_market("us_semi")

    def get_all_tickers(self) -> list[str]:
        return list(self._stocks.keys())

    def get_name(self, ticker: str) -> str:
        info = self._stocks.get(ticker)
        return info.name if info else ticker


_universe: StockUniverse | None = None

def get_stock_universe() -> StockUniverse:
    global _universe
    if _universe is None:
        _universe = StockUniverse()
    return _universe
