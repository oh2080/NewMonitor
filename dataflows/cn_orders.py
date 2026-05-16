"""订单/公告数据采集"""
import logging
from datetime import datetime, timedelta
from typing import List

import akshare as ak

from config.stock_universe import get_stock_universe
from models.news_item import NewsItem
from .base import BaseFetcher

logger = logging.getLogger(__name__)


class CNOrderFetcher(BaseFetcher):
    """A股公告/订单采集器"""

    ORDER_KEYWORDS = [
        "签署", "合同", "中标", "战略合作", "金额", "订单", "采购",
        "框架协议", "中标通知书", "项目合同", "供货合同", "销售合同",
        "重大合同", "投资", "产能", "扩产", "投产",
    ]

    EXCLUDE_KEYWORDS = [
        "减持", "质押", "解禁", "诉讼", "违规", "处罚", "退市",
        "停牌", "复牌", "股东大会",
    ]

    def __init__(self):
        super().__init__("cn_orders")

    def fetch(self) -> List[NewsItem]:
        items = []
        universe = get_stock_universe()
        cn_stocks = universe.get_cn_stocks()

        # 获取最近几天的公告
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=3)).strftime("%Y%m%d")

        for stock in cn_stocks:
            try:
                # 使用巨潮资讯接口
                df = ak.stock_notice_report(symbol=stock.symbol)
                if df is None or df.empty:
                    continue

                for _, row in df.head(10).iterrows():
                    title = str(row.get("公告标题", row.get("title", "")))

                    # 排除负面公告
                    if any(kw in title for kw in self.EXCLUDE_KEYWORDS):
                        continue

                    # 匹配订单相关
                    if not any(kw in title for kw in self.ORDER_KEYWORDS):
                        continue

                    item = NewsItem(
                        source="cninfo",
                        title=title,
                        content=str(row.get("公告内容", row.get("content", "")))[:500] if "公告内容" in row.index or "content" in row.index else title,
                        published_at=row.get("公告日期", row.get("datetime", None)),
                        related_tickers=[stock.symbol],
                        news_type="order",
                        url=str(row.get("公告链接", row.get("url", ""))) if "公告链接" in row.index or "url" in row.index else "",
                        extra={"stock_name": stock.name},
                    )
                    items.append(item)
            except Exception as e:
                logger.debug(f"获取 {stock.symbol} 公告失败: {e}")

        # 也尝试获取全部公告后过滤
        if not items:
            items = self._fetch_recent_announcements(start_date, end_date)

        self._save_cache(items)
        logger.info(f"订单/公告获取 {len(items)} 条")
        return items

    def _fetch_recent_announcements(self, start_date: str, end_date: str) -> List[NewsItem]:
        """备用方案：获取最近的公告列表"""
        items = []
        try:
            df = ak.stock_notice_report(symbol="全部")
            if df is not None and not df.empty:
                for _, row in df.head(50).iterrows():
                    title = str(row.get("公告标题", row.get("title", "")))
                    if any(kw in title for kw in self.EXCLUDE_KEYWORDS):
                        continue
                    if not any(kw in title for kw in self.ORDER_KEYWORDS):
                        continue

                    item = NewsItem(
                        source="cninfo",
                        title=title,
                        content=title,
                        published_at=row.get("公告日期", row.get("datetime", None)),
                        news_type="order",
                    )
                    items.append(item)
        except Exception as e:
            logger.warning(f"备用公告获取失败: {e}")

        return items
