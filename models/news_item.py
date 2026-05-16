"""新闻条目数据模型"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    """单条新闻/公告/情绪数据"""
    source: str = Field(description="数据源 (finnhub, yfinance, akshare, eastmoney, cninfo, reddit, guba)")
    title: str = Field(description="标题")
    content: str = Field(default="", description="正文摘要")
    published_at: Optional[datetime] = Field(default=None, description="发布时间")
    related_tickers: list[str] = Field(default_factory=list, description="相关股票代码")
    sentiment: Optional[str] = Field(default=None, description="情绪标签: positive/negative/neutral")
    news_type: str = Field(default="news", description="类型: news, order, sentiment")
    url: Optional[str] = Field(default=None, description="原文链接")
    extra: dict = Field(default_factory=dict, description="额外数据(如订单金额等)")
