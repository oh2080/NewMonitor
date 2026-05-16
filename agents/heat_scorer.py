"""热度评分引擎"""
import json
from typing import List

from config.settings import get_settings
from config.stock_universe import get_stock_universe
from models.stock_signal import StockSignal
from models.heat_report import HeatReport
from .base import BaseAgent


class HeatScorer(BaseAgent):
    """热度评分 Agent"""

    SYSTEM_PROMPT = """你是一位量化评分专家。基于以下分析结果，对每只股票的热度评分进行微调。

规则：
1. 你可以在算法评分基础上 ±10 分进行调整
2. 必须给出调整理由
3. 考虑综合因素：新闻热度、订单含金量、情绪方向、跨市场催化

输出格式（JSON）：
{
  "adjustments": [
    {
      "ticker": "688256",
      "adjustment": 5,
      "reason": "调整理由"
    }
  ],
  "overall_insight": "一句话总结当前市场最值得关注的方向"
}"""

    def __init__(self):
        super().__init__("heat_scorer")

    def analyze(self, research_data: dict, raw_news: dict) -> HeatReport:
        """计算热度评分并生成报告"""
        settings = get_settings()
        weights = settings.scoring_weights
        w_news = weights.get("news_frequency", 0.30)
        w_sentiment = weights.get("sentiment", 0.20)
        w_order = weights.get("order_signal", 0.50)

        stock_signals = research_data.get("stock_signals", [])
        universe = get_stock_universe()

        # 算法评分
        signals = self._compute_scores(stock_signals, raw_news, w_news, w_sentiment, w_order, universe)

        # LLM 微调
        signals = self._llm_adjust(signals)

        # 排序
        signals.sort(key=lambda s: s.heat_score, reverse=True)

        # 生成报告
        report = HeatReport(
            ranked_stocks=signals,
            us_news_summary=raw_news.get("us_news_summary", ""),
            cn_news_summary=raw_news.get("cn_news_summary", ""),
            order_summary=raw_news.get("order_summary", ""),
            sentiment_summary=raw_news.get("sentiment_summary", ""),
            cross_market_insight=research_data.get("cross_market_analysis", ""),
            keywords=research_data.get("hot_keywords", []),
            hidden_opportunities=research_data.get("hidden_opportunities", []),
        )

        return report

    def _compute_scores(self, stock_signals: list, raw_news: dict,
                        w_news: float, w_sentiment: float, w_order: float,
                        universe) -> List[StockSignal]:
        """算法评分"""
        signals = []

        # 统计新闻频率
        news_counts: dict[str, int] = {}
        for key, items in raw_news.get("all_news", {}).items():
            for item in items:
                for ticker in item.related_tickers:
                    news_counts[ticker] = news_counts.get(ticker, 0) + 1

        max_news = max(news_counts.values()) if news_counts else 1

        for sig_data in stock_signals:
            ticker = sig_data.get("ticker", "")
            name = universe.get_name(ticker)
            info = universe._stocks.get(ticker)

            news_count = news_counts.get(ticker, 0)
            news_freq_score = min(100, (news_count / max_news) * 100) if max_news > 0 else 0

            # 情绪评分
            sentiment = sig_data.get("heat_indicators", {}).get("sentiment", "neutral")
            sentiment_map = {"positive": 80, "negative": 20, "neutral": 50, "mixed": 50}
            sentiment_score = sentiment_map.get(sentiment, 50)

            # 订单信号评分
            has_order = sig_data.get("heat_indicators", {}).get("has_order_signal", False)
            order_score = 80 if has_order else 20

            # 综合评分
            heat_score = w_news * news_freq_score + w_sentiment * sentiment_score + w_order * order_score

            signal = StockSignal(
                ticker=ticker,
                name=name,
                market=info.market if info else "",
                news_count=news_count,
                heat_reasons=sig_data.get("reasons", []),
                news_frequency_score=round(news_freq_score, 1),
                sentiment_score=sentiment_score,
                order_signal_score=order_score,
                heat_score=round(heat_score, 1),
                llm_insight=sig_data.get("cross_market_link", ""),
            )
            signals.append(signal)

        return signals

    def _llm_adjust(self, signals: List[StockSignal]) -> List[StockSignal]:
        """LLM 微调评分"""
        if not signals:
            return signals

        signals_text = "\n".join([
            f"{s.ticker} ({s.name}): 算法评分={s.heat_score}, 新闻频率={s.news_frequency_score}, 情绪={s.sentiment_score}, 订单={s.order_signal_score}, 原因={s.heat_reasons[:2]}"
            for s in signals[:15]
        ])

        prompt = f"请对以下股票的热度评分进行微调 (±10分)：\n\n{self._truncate_text(signals_text)}"

        try:
            result = self.llm.chat_json(prompt, self.SYSTEM_PROMPT, temperature=0.2, use_deep=False)
            adjustments = {a["ticker"]: a for a in result.get("adjustments", [])}

            for signal in signals:
                adj = adjustments.get(signal.ticker)
                if adj:
                    signal.llm_adjustment = adj.get("adjustment", 0)
                    signal.heat_score = max(0, min(100, signal.heat_score + signal.llm_adjustment))
                    signal.heat_score = round(signal.heat_score, 1)

            self.logger.info(f"LLM微调完成: {len(adjustments)} 只股票")
        except Exception as e:
            self.logger.warning(f"LLM微调失败: {e}")

        return signals
