"""情绪分析师"""
from typing import List

from models.news_item import NewsItem
from .base import BaseAgent


class SentimentAnalyst(BaseAgent):
    """市场情绪分析 Agent"""

    SYSTEM_PROMPT = """你是一位市场情绪分析专家，专注于分析散户和机构对 AI/半导体板块的关注度和情绪。

分析维度：
1. 整体市场情绪（乐观/悲观/观望）
2. 散户关注度变化（论坛讨论热度）
3. 资金流向信号
4. 是否出现过热或恐慌信号

输出格式（JSON）：
{
  "overall_sentiment": "positive/negative/neutral/mixed",
  "sentiment_score": 0.7,
  "retail_attention": "散户关注度描述",
  "hot_discussions": [
    {"topic": "讨论话题", "ticker": "相关代码", "tone": "乐观/悲观/观望"}
  ],
  "warning_signals": ["风险信号1"],
  "keywords": ["关键词1", "关键词2"]
}"""

    def __init__(self):
        super().__init__("sentiment_analyst")

    def analyze(self, news_items: List[NewsItem]) -> dict:
        if not news_items:
            return {"overall_sentiment": "neutral", "sentiment_score": 0.5, "retail_attention": "无数据", "hot_discussions": [], "warning_signals": [], "keywords": []}

        sentiment_text = "\n".join([
            f"[{item.source}] {item.title}\n  {item.content[:150]}"
            for item in news_items[:30]
        ])

        prompt = f"请分析以下 {len(news_items)} 条社交情绪数据：\n\n{self._truncate_text(sentiment_text)}"

        try:
            result = self.llm.chat_json(prompt, self.SYSTEM_PROMPT, temperature=0.3, use_deep=False)
            self.logger.info(f"情绪分析完成: {result.get('overall_sentiment', 'unknown')}")
            return result
        except Exception as e:
            self.logger.error(f"情绪分析失败: {e}")
            return {"overall_sentiment": "neutral", "sentiment_score": 0.5, "retail_attention": "分析失败", "hot_discussions": [], "warning_signals": [], "keywords": []}
