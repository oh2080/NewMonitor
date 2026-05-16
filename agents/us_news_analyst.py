"""美股新闻分析师"""
from typing import List

from models.news_item import NewsItem
from models.stock_signal import StockSignal
from .base import BaseAgent


class USNewsAnalyst(BaseAgent):
    """美股新闻分析 Agent"""

    SYSTEM_PROMPT = """你是一位资深的美股科技股分析师，专精于 AI/半导体行业。
你的任务是分析美股 AI/半导体相关新闻，提取关键信息，并判断对 A 股半导体板块的影响。

分析维度：
1. 关键技术突破或产品发布（如新 GPU、HBM 进展）
2. 供应链变化（如台积电产能、CoWoS 扩产）
3. 财报关键指标（如数据中心收入、AI 相关增速）
4. 行业趋势（如 AI 算力需求、数据中心资本开支）

输出格式（JSON）：
{
  "summary": "美股AI/半导体板块整体动态摘要(200字以内)",
  "key_events": [
    {"event": "事件描述", "impact_stocks": ["相关A股代码"], "reason": "影响原因"}
  ],
  "a_share_mapping": [
    {"cn_ticker": "A股代码", "cn_name": "A股名称", "us_driver": "美股驱动事件", "logic": "传导逻辑"}
  ],
  "keywords": ["关键词1", "关键词2"],
  "sentiment": "positive/negative/neutral",
  "sentiment_reason": "情绪判断理由"
}"""

    def __init__(self):
        super().__init__("us_news_analyst")

    def analyze(self, news_items: List[NewsItem]) -> dict:
        if not news_items:
            return {"summary": "无美股新闻数据", "key_events": [], "a_share_mapping": [], "keywords": [], "sentiment": "neutral"}

        # 构造新闻摘要
        news_text = "\n".join([
            f"[{item.published_at or '未知时间'}] {item.title}\n  摘要: {item.content[:200]}"
            for item in news_items[:40]
        ])

        prompt = f"请分析以下 {len(news_items)} 条美股 AI/半导体相关新闻：\n\n{self._truncate_text(news_text)}"

        try:
            result = self.llm.chat_json(prompt, self.SYSTEM_PROMPT, temperature=0.3, use_deep=False)
            self.logger.info(f"美股新闻分析完成: {len(result.get('key_events', []))} 个关键事件")
            return result
        except Exception as e:
            self.logger.error(f"美股新闻分析失败: {e}")
            return {"summary": f"分析失败: {e}", "key_events": [], "a_share_mapping": [], "keywords": [], "sentiment": "neutral"}
