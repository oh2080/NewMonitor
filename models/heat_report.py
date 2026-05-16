"""热度报告数据模型"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from .stock_signal import StockSignal


class HeatReport(BaseModel):
    """最终热度报告"""
    generated_at: datetime = Field(default_factory=datetime.now, description="生成时间")
    ranked_stocks: list[StockSignal] = Field(default_factory=list, description="按热度排序的股票列表")

    # 各维度摘要
    us_news_summary: str = Field(default="", description="美股新闻摘要")
    cn_news_summary: str = Field(default="", description="A股新闻摘要")
    order_summary: str = Field(default="", description="订单信号摘要")
    sentiment_summary: str = Field(default="", description="情绪概览")

    # LLM 洞察
    cross_market_insight: str = Field(default="", description="跨市场关联分析")
    keywords: list[str] = Field(default_factory=list, description="热门关键词")
    hidden_opportunities: list[str] = Field(default_factory=list, description="被忽视的机会")
