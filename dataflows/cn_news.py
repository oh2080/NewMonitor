"""A股新闻数据采集"""
import logging
from datetime import datetime
from typing import List

import akshare as ak
import pandas as pd

from config.settings import get_settings
from config.stock_universe import get_stock_universe
from models.news_item import NewsItem
from .base import BaseFetcher

logger = logging.getLogger(__name__)


class CNNewsFetcher(BaseFetcher):
    """A股新闻采集器"""

    AI_KEYWORDS = [
        "AI", "人工智能", "芯片", "半导体", "GPU", "算力", "光刻", "封测",
        "HBM", "存储", "国产替代", "大模型", "信创", "晶圆", "代工",
        "英伟达", "台积电", "华为", "寒武纪", "海光", "中芯",
    ]

    def __init__(self):
        super().__init__("cn_news")

    def fetch(self) -> List[NewsItem]:
        items = []
        settings = get_settings()
        ds = settings.data_sources.get("cn_news", {})

        if ds.get("akshare", True):
            items.extend(self._fetch_akshare_cctv())
            items.extend(self._fetch_akshare_stock_news())

        if ds.get("eastmoney", True):
            items.extend(self._fetch_concept_ths())

        self._save_cache(items)
        return items

    def _fetch_akshare_cctv(self) -> List[NewsItem]:
        """获取央视财经新闻"""
        items = []
        try:
            df = ak.news_cctv(date=datetime.now().strftime("%Y%m%d"))
            if df is not None and not df.empty:
                for _, row in df.head(30).iterrows():
                    title = str(row.get("title", ""))
                    content = str(row.get("content", ""))[:500]
                    text = f"{title} {content}"

                    if not any(kw in text for kw in self.AI_KEYWORDS):
                        continue

                    item = NewsItem(
                        source="akshare_cctv",
                        title=title,
                        content=content,
                        published_at=row.get("date", None),
                        news_type="news",
                    )
                    items.append(item)
        except Exception as e:
            logger.warning(f"获取央视新闻失败: {e}")

        logger.info(f"央视新闻获取 {len(items)} 条AI相关")
        return items

    def _fetch_akshare_stock_news(self) -> List[NewsItem]:
        """获取个股新闻"""
        items = []
        universe = get_stock_universe()
        cn_stocks = universe.get_cn_stocks()

        for stock in cn_stocks[:10]:  # 限制数量避免API限制
            try:
                df = ak.stock_news_em(symbol=stock.symbol)
                if df is not None and not df.empty:
                    for _, row in df.head(5).iterrows():
                        item = NewsItem(
                            source="akshare_stock",
                            title=str(row.get("新闻标题", "")),
                            content=str(row.get("新闻内容", ""))[:500],
                            published_at=row.get("发布时间", None),
                            related_tickers=[stock.symbol],
                            news_type="news",
                            url=str(row.get("新闻链接", "")),
                        )
                        items.append(item)
            except Exception as e:
                logger.warning(f"获取 {stock.symbol} 新闻失败: {e}")

        logger.info(f"A股个股新闻获取 {len(items)} 条")
        return items

    def _fetch_concept_ths(self) -> List[NewsItem]:
        """获取概念板块动态（同花顺数据源）"""
        items = []
        concept_keywords = ["半导体", "芯片", "AI", "人工智能", "算力"]

        try:
            # 获取同花顺概念板块列表（只调一次，约5-10秒）
            df = ak.stock_board_concept_name_ths()
            if df is None or df.empty:
                logger.info("概念板块动态获取 0 条")
                return items

            for kw in concept_keywords:
                try:
                    matched = df[df["name"].str.contains(kw, na=False)]
                    for _, row in matched.head(3).iterrows():
                        concept_name = row.get("name", "")
                        concept_code = row.get("code", "")

                        item = NewsItem(
                            source="ths_concept",
                            title=f"概念板块: {concept_name}",
                            content=f"板块代码: {concept_code}",
                            related_tickers=[],
                            news_type="news",
                            extra={"concept": concept_name, "code": concept_code},
                        )
                        items.append(item)
                except Exception as e:
                    logger.warning(f"匹配概念板块 '{kw}' 失败: {e}")
        except Exception as e:
            logger.warning(f"同花顺概念板块获取失败: {e}")

        logger.info(f"概念板块动态获取 {len(items)} 条")
        return items
