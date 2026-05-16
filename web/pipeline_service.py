"""可复用的流水线服务（带进度回调）"""
import logging
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Callable, Optional

from web.progress import (
    PipelineStatus, emit, get_state, reset_state,
)

logger = logging.getLogger(__name__)

# 进度回调类型: (event_name: str, data: dict) -> None
ProgressCallback = Callable[[str, dict], None]


class PipelineService:
    """封装完整的分析流水线，支持进度回调"""

    def __init__(self, callback: Optional[ProgressCallback] = None):
        self._cb = callback or (lambda e, d: None)
        self._emit = lambda e, d: (emit(e, d), self._cb(e, d))

    def run(self):
        """执行完整流水线"""
        state = get_state()
        reset_state()

        state.status = PipelineStatus.RUNNING
        state.started_at = __import__("time").time()

        self._emit("pipeline_start", {"message": "流水线启动"})

        try:
            # 预检 LLM
            llm_ok = self._check_llm()
            if not llm_ok:
                self._emit("log", {"level": "warn", "message": "LLM API 不可用，仅保存原始数据"})

            # Phase 1
            raw_data = self._phase1_fetch()
            state.raw_data = raw_data

            total = sum(len(v) for v in raw_data.values())
            if total == 0:
                raise RuntimeError("未获取到任何数据，请检查网络连接和API配置")

            if not llm_ok:
                from models.heat_report import HeatReport
                report = HeatReport()
            else:
                # Phase 2
                analyst_reports = self._phase2_analyze(raw_data)
                state.analyst_reports = analyst_reports

                # Phase 3
                report = self._phase3_score(analyst_reports, raw_data)

            state.report = report
            state.status = PipelineStatus.DONE
            state.finished_at = __import__("time").time()

            self._emit("pipeline_done", {
                "message": "分析完成",
                "stock_count": len(report.ranked_stocks),
                "elapsed": round(state.finished_at - state.started_at, 1),
            })

            # 保存报告
            try:
                from output.file_writer import save_report
                path = save_report(report)
                self._emit("log", {"level": "info", "message": f"报告已保存: {path}"})
            except Exception as e:
                logger.warning(f"保存报告失败: {e}")

        except Exception as e:
            state.status = PipelineStatus.ERROR
            state.error_message = str(e)
            state.finished_at = __import__("time").time()
            self._emit("pipeline_error", {"message": str(e), "traceback": traceback.format_exc()})
            logger.error(f"流水线错误: {e}\n{traceback.format_exc()}")

    def _check_llm(self) -> bool:
        """预检 LLM API"""
        self._emit("log", {"level": "info", "message": "检查 LLM API 连接..."})
        try:
            from llm.glm_client import get_llm_client
            client = get_llm_client()
            client.quick_classify("回复OK", "你是API健康检查助手")
            self._emit("log", {"level": "info", "message": "GLM API 连接正常"})
            return True
        except Exception as e:
            err = str(e)
            if "1113" in err or "余额不足" in err:
                self._emit("log", {"level": "error", "message": "GLM API 余额不足"})
            else:
                self._emit("log", {"level": "error", "message": f"GLM API 连接失败: {e}"})
            return False

    def _phase1_fetch(self) -> dict:
        """Phase 1: 并行数据采集"""
        from dataflows.us_news import USNewsFetcher
        from dataflows.cn_news import CNNewsFetcher
        from dataflows.cn_orders import CNOrderFetcher
        from dataflows.sentiment import SentimentFetcher

        self._emit("phase_start", {"phase": 1, "message": "数据采集 (4个数据源并行)"})
        get_state().current_phase = "phase1"

        fetchers = {
            "us_news": USNewsFetcher(),
            "cn_news": CNNewsFetcher(),
            "cn_orders": CNOrderFetcher(),
            "sentiment": SentimentFetcher(),
        }

        # 通知所有 fetcher 开始
        for name in fetchers:
            get_state().fetcher_status[name] = "running"
            self._emit("fetcher_started", {"name": name})

        results = {}
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = {
                executor.submit(fetcher.fetch): name
                for name, fetcher in fetchers.items()
            }

            for future in as_completed(futures):
                name = futures[future]
                try:
                    items = future.result()
                    results[name] = items
                    get_state().fetcher_status[name] = "done"
                    self._emit("fetcher_done", {"name": name, "count": len(items)})
                except Exception as e:
                    results[name] = []
                    get_state().fetcher_status[name] = "fail"
                    self._emit("fetcher_done", {"name": name, "count": 0, "error": str(e)})
                    self._emit("log", {"level": "error", "message": f"{name} 采集失败: {e}"})

        self._emit("phase_done", {"phase": 1, "message": "数据采集完成"})
        return results

    def _phase2_analyze(self, raw_data: dict) -> dict:
        """Phase 2: 串行数据分析"""
        from agents.us_news_analyst import USNewsAnalyst
        from agents.cn_news_analyst import CNNewsAnalyst
        from agents.order_analyst import OrderAnalyst
        from agents.sentiment_analyst import SentimentAnalyst

        self._emit("phase_start", {"phase": 2, "message": "数据分析 (串行调用LLM)"})
        get_state().current_phase = "phase2"

        analysts = [
            ("sentiment", SentimentAnalyst(), raw_data.get("sentiment", [])),
            ("us_news", USNewsAnalyst(), raw_data.get("us_news", [])),
            ("cn_news", CNNewsAnalyst(), raw_data.get("cn_news", [])),
            ("orders", OrderAnalyst(), raw_data.get("cn_orders", [])),
        ]

        results = {}
        for name, analyst, data in analysts:
            get_state().analyst_status[name] = "running"
            self._emit("analyst_started", {"name": name})

            try:
                result = analyst.analyze(data)
                results[name] = result
                get_state().analyst_status[name] = "done"
                self._emit("analyst_done", {"name": name})
            except Exception as e:
                results[name] = {}
                get_state().analyst_status[name] = "fail"
                self._emit("analyst_done", {"name": name, "error": str(e)})
                self._emit("log", {"level": "error", "message": f"{name} 分析失败: {e}"})

            # 检查余额不足
            summary = results[name].get("summary", "")
            if "余额不足" in summary or "充值" in summary:
                self._emit("log", {"level": "error", "message": "GLM API 余额不足，跳过后续分析"})
                remaining = [n for n, _, _ in analysts if n not in results]
                for n in remaining:
                    results[n] = {}
                    get_state().analyst_status[n] = "fail"
                    self._emit("analyst_done", {"name": n, "error": "余额不足，已跳过"})
                break

        self._emit("phase_done", {"phase": 2, "message": "数据分析完成"})
        return results

    def _phase3_score(self, analyst_reports: dict, raw_data: dict):
        """Phase 3: 研究主管 + 热度评分"""
        from agents.research_lead import ResearchLead
        from agents.heat_scorer import HeatScorer

        self._emit("phase_start", {"phase": 3, "message": "研究主管汇总分析"})
        get_state().current_phase = "phase3"

        # Research Lead
        get_state().analyst_status["research_lead"] = "running"
        self._emit("analyst_started", {"name": "research_lead"})

        lead = ResearchLead()
        research_data = lead.analyze(analyst_reports)
        get_state().analyst_status["research_lead"] = "done"
        self._emit("analyst_done", {"name": "research_lead"})

        # Heat Scorer
        self._emit("phase_progress", {"phase": 3, "message": "热度评分与排名"})
        get_state().analyst_status["heat_scorer"] = "running"
        self._emit("analyst_started", {"name": "heat_scorer"})

        raw_for_scorer = {
            "all_news": {
                "us": raw_data.get("us_news", []),
                "cn": raw_data.get("cn_news", []),
                "orders": raw_data.get("cn_orders", []),
                "sentiment": raw_data.get("sentiment", []),
            },
            "us_news_summary": analyst_reports.get("us_news", {}).get("summary", ""),
            "cn_news_summary": analyst_reports.get("cn_news", {}).get("summary", ""),
            "order_summary": analyst_reports.get("orders", {}).get("summary", ""),
            "sentiment_summary": analyst_reports.get("sentiment", {}).get("summary", ""),
        }

        scorer = HeatScorer()
        report = scorer.analyze(research_data, raw_for_scorer)
        get_state().analyst_status["heat_scorer"] = "done"
        self._emit("analyst_done", {"name": "heat_scorer"})

        self._emit("phase_done", {"phase": 3, "message": "评分完成"})
        return report
