"""股票信号数据模型"""
from typing import Optional

from pydantic import BaseModel, Field


class StockSignal(BaseModel):
    """单只股票的综合信号"""
    ticker: str = Field(description="股票代码")
    name: str = Field(default="", description="股票名称")
    market: str = Field(default="", description="市场: us_semi, cn_semi, cn_ai")

    # 原始数据
    news_count: int = Field(default=0, description="相关新闻数量")
    news_items: list[str] = Field(default_factory=list, description="关键新闻标题列表")
    order_signals: list[str] = Field(default_factory=list, description="订单/公告信号列表")
    sentiment_summary: str = Field(default="", description="情绪摘要")

    # 评分维度
    news_frequency_score: float = Field(default=0.0, description="新闻频率得分 (0-100)")
    sentiment_score: float = Field(default=50.0, description="情绪得分 (0-100, 50为中性)")
    order_signal_score: float = Field(default=0.0, description="订单信号得分 (0-100)")

    # 综合得分
    heat_score: float = Field(default=0.0, description="综合热度分 (0-100)")

    # LLM 分析
    heat_reasons: list[str] = Field(default_factory=list, description="热度原因")
    llm_adjustment: float = Field(default=0.0, description="LLM微调分数 (±10)")
    llm_insight: str = Field(default="", description="LLM洞察")
