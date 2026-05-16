"""A股新闻分析师"""
from typing import List

from models.news_item import NewsItem
from .base import BaseAgent


class CNNewsAnalyst(BaseAgent):
    """A股新闻分析 Agent"""

    SYSTEM_PROMPT = """你是一位资深的 A 股半导体/AI 行业分析师。
分析国内 AI 和半导体产业新闻，重点关注：

1. 政策动向（国产替代、集成电路政策、算力基建）
2. 产业进展（国产 GPU、HBM、先进封装、光刻突破）
3. 公司动态（业绩预告、产能扩张、技术合作）
4. 概念板块（资金流向、板块轮动）

输出格式（JSON）：
{
  "summary": "A股AI/半导体板块整体动态摘要(200字以内)",
  "policy_signals": ["政策信号1", "政策信号2"],
  "industry_progress": [
    {"company": "公司名", "ticker": "代码", "progress": "进展描述", "significance": "重要性(高/中/低)"}
  ],
  "hot_concepts": ["热门概念1", "热门概念2"],
  "keywords": ["关键词1", "关键词2"],
  "sentiment": "positive/negative/neutral",
  "sentiment_reason": "情绪判断理由"
}"""

    def __init__(self):
        super().__init__("cn_news_analyst")

    def analyze(self, news_items: List[NewsItem]) -> dict:
        if not news_items:
            return {"summary": "无A股新闻数据", "policy_signals": [], "industry_progress": [], "hot_concepts": [], "keywords": [], "sentiment": "neutral"}

        news_text = "\n".join([
            f"[{item.source}] {item.title}\n  内容: {item.content[:200]}"
            for item in news_items[:40]
        ])

        prompt = f"请分析以下 {len(news_items)} 条 A 股 AI/半导体相关新闻：\n\n{self._truncate_text(news_text)}"

        try:
            result = self.llm.chat_json(prompt, self.SYSTEM_PROMPT, temperature=0.3, use_deep=False)
            self.logger.info(f"A股新闻分析完成: {len(result.get('industry_progress', []))} 条产业进展")
            return result
        except Exception as e:
            self.logger.error(f"A股新闻分析失败: {e}")
            return {"summary": f"分析失败: {e}", "policy_signals": [], "industry_progress": [], "hot_concepts": [], "keywords": [], "sentiment": "neutral"}
