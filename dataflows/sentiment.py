"""社交情绪数据采集"""
import logging
from datetime import datetime
from typing import List

from config.settings import get_settings
from config.stock_universe import get_stock_universe
from models.news_item import NewsItem
from .base import BaseFetcher

logger = logging.getLogger(__name__)


class SentimentFetcher(BaseFetcher):
    """社交情绪采集器"""

    def __init__(self):
        super().__init__("sentiment")

    def fetch(self) -> List[NewsItem]:
        items = []
        settings = get_settings()
        ds = settings.data_sources.get("sentiment", {})

        if ds.get("eastmoney_guba", True):
            items.extend(self._fetch_eastmoney_guba())

        if ds.get("reddit", False):
            items.extend(self._fetch_reddit())

        self._save_cache(items)
        return items

    def _fetch_eastmoney_guba(self) -> List[NewsItem]:
        """东方财富千股千评（替代已移除的股吧接口）"""
        items = []
        try:
            import akshare as ak
            universe = get_stock_universe()
            cn_stocks = universe.get_cn_stocks()
            target_symbols = {s.symbol for s in cn_stocks}

            df = ak.stock_comment_em()
            if df is not None and not df.empty:
                # 筛选自选股
                matched = df[df["代码"].isin(target_symbols)]
                for _, row in matched.iterrows():
                    name = str(row.get("名称", ""))
                    code = str(row.get("代码", ""))
                    score = str(row.get("综合得分", ""))
                    attention = str(row.get("关注指数", ""))
                    direction = str(row.get("目前方向", ""))

                    item = NewsItem(
                        source="eastmoney_comment",
                        title=f"千股千评: {name}({code})",
                        content=f"综合得分: {score}, 关注指数: {attention}, 目前方向: {direction}, 涨跌幅: {row.get('涨跌幅', 'N/A')}%",
                        related_tickers=[code],
                        news_type="sentiment",
                        extra={
                            "stock_name": name,
                            "score": score,
                            "attention_index": attention,
                            "direction": direction,
                        },
                    )
                    items.append(item)
        except Exception as e:
            logger.warning(f"千股千评采集失败: {e}")

        logger.info(f"千股千评数据获取 {len(items)} 条")
        return items

    def _fetch_reddit(self) -> List[NewsItem]:
        """Reddit 社交情绪"""
        items = []
        try:
            import httpx
            import os

            # Reddit 公开 JSON API（无需认证）
            subreddits = ["wallstreetbets", "stocks", "technology"]
            keywords = ["AI", "chip", "semiconductor", "NVIDIA", "AMD", "TSMC", "GPU"]

            for sub in subreddits:
                try:
                    url = f"https://www.reddit.com/r/{sub}/hot.json?limit=25"
                    resp = httpx.get(url, headers={"User-Agent": "NewsMonitor/1.0"}, timeout=10)
                    if resp.status_code != 200:
                        continue

                    data = resp.json()
                    for post in data.get("data", {}).get("children", []):
                        d = post.get("data", {})
                        title = d.get("title", "")
                        text = f"{title} {d.get('selftext', '')}"

                        if not any(kw.lower() in text.lower() for kw in keywords):
                            continue

                        item = NewsItem(
                            source="reddit",
                            title=title,
                            content=d.get("selftext", "")[:300],
                            published_at=datetime.fromtimestamp(d.get("created_utc", 0)),
                            related_tickers=[],
                            news_type="sentiment",
                            url=f"https://reddit.com{d.get('permalink', '')}",
                            extra={
                                "subreddit": sub,
                                "score": d.get("score", 0),
                                "num_comments": d.get("num_comments", 0),
                            },
                        )
                        items.append(item)
                except Exception as e:
                    logger.debug(f"Reddit r/{sub} 获取失败: {e}")
        except Exception as e:
            logger.warning(f"Reddit 采集失败: {e}")

        logger.info(f"Reddit 获取 {len(items)} 条AI相关帖子")
        return items
