"""美股新闻数据采集"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import yfinance as yf

from config.settings import get_settings
from config.stock_universe import get_stock_universe
from models.news_item import NewsItem
from .base import BaseFetcher

logger = logging.getLogger(__name__)


class USNewsFetcher(BaseFetcher):
    """美股新闻采集器"""

    def __init__(self):
        super().__init__("us_news")

    def fetch(self) -> List[NewsItem]:
        items = []
        settings = get_settings()
        ds = settings.data_sources.get("us_news", {})

        if ds.get("yfinance", True):
            items.extend(self._fetch_yfinance())

        if ds.get("finnhub", False) and settings.llm.get("api_key"):
            items.extend(self._fetch_finnhub())

        self._save_cache(items)
        return items

    def _fetch_yfinance(self) -> List[NewsItem]:
        """通过 yfinance 获取个股新闻"""
        items = []
        universe = get_stock_universe()
        us_stocks = universe.get_us_stocks()

        for stock in us_stocks:
            try:
                ticker = yf.Ticker(stock.symbol)
                news_list = ticker.news or []
                for n in news_list[:5]:  # 每只股票取最近5条
                    item = NewsItem(
                        source="yfinance",
                        title=n.get("title", ""),
                        content=n.get("summary", n.get("title", ""))[:500],
                        published_at=datetime.fromtimestamp(n.get("providerPublishTime", 0)) if n.get("providerPublishTime") else None,
                        related_tickers=[stock.symbol],
                        news_type="news",
                        url=n.get("link", ""),
                    )
                    items.append(item)
            except Exception as e:
                logger.warning(f"获取 {stock.symbol} 新闻失败: {e}")

        logger.info(f"yfinance 获取 {len(items)} 条美股新闻")
        return items

    def _fetch_finnhub(self) -> List[NewsItem]:
        """通过 Finnhub API 获取市场新闻"""
        items = []
        try:
            import finnhub
            api_key = get_settings().data_sources.get("us_news", {}).get("finnhub_api_key", "")
            if not api_key:
                import os
                api_key = os.environ.get("FINNHUB_API_KEY", "")
            if not api_key:
                return items

            finnhub_client = finnhub.Client(api_key=api_key)
            # 获取半导体行业新闻
            news = finnhub_client.general_news("technology", min_id=0)

            ai_keywords = ["AI", "chip", "semiconductor", "GPU", "NVIDIA", "AMD", "Intel",
                          "TSMC", "HBM", "data center", "artificial intelligence"]

            for n in (news or [])[:30]:
                title = n.get("headline", "")
                summary = n.get("summary", "")
                text = f"{title} {summary}".lower()

                # 过滤 AI/半导体相关
                if not any(kw.lower() in text for kw in ai_keywords):
                    continue

                # 提取相关美股代码
                related = n.get("related", "")
                tickers = [t.strip() for t in related.split(",") if t.strip()] if related else []

                item = NewsItem(
                    source="finnhub",
                    title=title,
                    content=summary[:500],
                    published_at=datetime.fromtimestamp(n.get("datetime", 0)) if n.get("datetime") else None,
                    related_tickers=tickers,
                    news_type="news",
                    url=n.get("url", ""),
                )
                items.append(item)
        except Exception as e:
            logger.warning(f"Finnhub 获取失败: {e}")

        logger.info(f"Finnhub 获取 {len(items)} 条科技新闻")
        return items
