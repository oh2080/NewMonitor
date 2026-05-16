"""订单/公告分析师"""
from typing import List

from models.news_item import NewsItem
from .base import BaseAgent


class OrderAnalyst(BaseAgent):
    """订单公告分析 Agent"""

    SYSTEM_PROMPT = """你是一位资深投资分析师，专注于分析上市公司公告中的订单和合同信息。

对每条公告进行评估：
1. 判断是否为实质性利好（真合同 vs 框架协议）
2. 评估金额规模（如有）
3. 行业地位和竞争格局影响
4. 对公司未来业绩的潜在影响

输出格式（JSON）：
{
  "summary": "近期重要订单/合同公告摘要(200字以内)",
  "important_orders": [
    {
      "ticker": "股票代码",
      "company": "公司名",
      "title": "公告标题",
      "significance": "高/中/低",
      "reason": "重要性判断理由",
      "estimated_impact": "预估影响"
    }
  ],
  "hot_sectors": ["热门细分方向1", "热门细分方向2"],
  "keywords": ["关键词1", "关键词2"]
}"""

    def __init__(self):
        super().__init__("order_analyst")

    def analyze(self, news_items: List[NewsItem]) -> dict:
        if not news_items:
            return {"summary": "无订单/公告数据", "important_orders": [], "hot_sectors": [], "keywords": []}

        order_text = "\n".join([
            f"[{item.related_tickers[0] if item.related_tickers else '未知'}] {item.title}"
            for item in news_items[:30]
        ])

        prompt = f"请分析以下 {len(news_items)} 条上市公司公告/订单信息：\n\n{self._truncate_text(order_text)}"

        try:
            result = self.llm.chat_json(prompt, self.SYSTEM_PROMPT, temperature=0.3, use_deep=False)
            self.logger.info(f"订单分析完成: {len(result.get('important_orders', []))} 条重要订单")
            return result
        except Exception as e:
            self.logger.error(f"订单分析失败: {e}")
            return {"summary": f"分析失败: {e}", "important_orders": [], "hot_sectors": [], "keywords": []}
