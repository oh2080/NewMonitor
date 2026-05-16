"""研究主管 - 汇总所有分析师的报告"""
import json
from typing import List

from config.stock_universe import get_stock_universe
from models.stock_signal import StockSignal
from .base import BaseAgent


class ResearchLead(BaseAgent):
    """研究主管 Agent - 跨市场关联分析"""

    SYSTEM_PROMPT = """你是一位首席研究分析师，负责整合美股动态、A股产业分析、订单信号和市场情绪，输出综合研判。

你的核心能力：
1. 跨市场关联：美股 AI 芯片动态 → A 股半导体映射（如英伟达HBM需求 → A股封测/存储链）
2. 关键词热度聚合：识别高频出现的技术关键词和投资主题
3. 机会识别：发现"新闻少但订单强"或"美股催化但A股未反应"的机会

输出格式（JSON）：
{
  "cross_market_analysis": "跨市场关联分析(300字以内)",
  "hot_keywords": ["AI芯片", "HBM3", ...],
  "stock_signals": [
    {
      "ticker": "688256",
      "name": "寒武纪",
      "market": "cn_semi",
      "heat_indicators": {
        "news_count": 5,
        "has_order_signal": true,
        "sentiment": "positive",
        "key_driver": "国产AI芯片突破"
      },
      "reasons": ["原因1", "原因2"],
      "cross_market_link": "美股映射逻辑（如有）"
    }
  ],
  "hidden_opportunities": [
    "被忽视的机会描述1",
    "被忽视的机会描述2"
  ],
  "risk_warnings": ["风险提示1"]
}"""

    def __init__(self):
        super().__init__("research_lead")

    def analyze(self, reports: dict) -> dict:
        """汇总4个分析师的报告"""
        prompt = f"""请整合以下分析师报告，输出综合研判：

## 美股分析师报告
{json.dumps(reports.get("us_news", {}), ensure_ascii=False, indent=2)[:3000]}

## A股分析师报告
{json.dumps(reports.get("cn_news", {}), ensure_ascii=False, indent=2)[:3000]}

## 订单分析师报告
{json.dumps(reports.get("orders", {}), ensure_ascii=False, indent=2)[:2000]}

## 情绪分析师报告
{json.dumps(reports.get("sentiment", {}), ensure_ascii=False, indent=2)[:2000]}
"""

        try:
            result = self.llm.chat_json(prompt, self.SYSTEM_PROMPT, temperature=0.4, use_deep=False)
            self.logger.info(f"研究主管分析完成: {len(result.get('stock_signals', []))} 只股票信号")
            return result
        except Exception as e:
            self.logger.error(f"研究主管分析失败: {e}")
            return {"cross_market_analysis": f"分析失败: {e}", "hot_keywords": [], "stock_signals": [], "hidden_opportunities": [], "risk_warnings": []}
