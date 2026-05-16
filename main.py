"""
NewsMonitor - AI热点股票监控系统
手动触发运行: python main.py
"""
import os
import sys

# Windows UTF-8 编码修复（必须在所有 import 之前）
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    os.environ.setdefault("PYTHONUTF8", "1")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 禁用系统代理（国内 API 直连更快更稳定）
os.environ.pop("HTTP_PROXY", None)
os.environ.pop("HTTPS_PROXY", None)
os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)
os.environ.pop("ALL_PROXY", None)
os.environ.pop("all_proxy", None)
os.environ["NO_PROXY"] = "*"

# 确保 requests 库也不走代理
import requests
requests.Session.trust_env = False

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# 设置项目根目录到 sys.path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from config.settings import get_settings
from config.stock_universe import get_stock_universe
from output.console import (
    print_header, print_phase, print_fetcher_status,
    print_analyst_status, print_report, print_error, print_done,
)
from output.file_writer import save_report


def setup_logging():
    """配置日志"""
    log_dir = ROOT / "logs"
    log_dir.mkdir(exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=[
            logging.FileHandler(
                log_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log",
                encoding="utf-8",
            ),
            logging.StreamHandler(),
        ],
    )


def phase1_fetch_data(executor: ThreadPoolExecutor) -> dict:
    """Phase 1: 并行数据采集"""
    print_phase("Phase 1", "数据采集 (4个数据源并行)")

    from dataflows.us_news import USNewsFetcher
    from dataflows.cn_news import CNNewsFetcher
    from dataflows.cn_orders import CNOrderFetcher
    from dataflows.sentiment import SentimentFetcher

    fetchers = {
        "us_news": USNewsFetcher(),
        "cn_news": CNNewsFetcher(),
        "cn_orders": CNOrderFetcher(),
        "sentiment": SentimentFetcher(),
    }

    results = {}
    futures = {
        executor.submit(fetcher.fetch): name
        for name, fetcher in fetchers.items()
    }

    for future in as_completed(futures):
        name = futures[future]
        try:
            items = future.result()
            results[name] = items
            print_fetcher_status(name, len(items))
        except Exception as e:
            results[name] = []
            print_fetcher_status(name, 0, "FAIL")
            print_error(f"{name} 采集失败: {e}")

    return results


def phase2_analyze(raw_data: dict) -> dict:
    """Phase 2: 串行数据分析（避免 LLM API 限流）"""
    print_phase("Phase 2", "数据分析 (串行调用LLM)")

    from agents.us_news_analyst import USNewsAnalyst
    from agents.cn_news_analyst import CNNewsAnalyst
    from agents.order_analyst import OrderAnalyst
    from agents.sentiment_analyst import SentimentAnalyst

    analysts = [
        ("sentiment", SentimentAnalyst(), raw_data.get("sentiment", [])),
        ("us_news", USNewsAnalyst(), raw_data.get("us_news", [])),
        ("cn_news", CNNewsAnalyst(), raw_data.get("cn_news", [])),
        ("orders", OrderAnalyst(), raw_data.get("cn_orders", [])),
    ]

    results = {}
    for name, analyst, data in analysts:
        try:
            result = analyst.analyze(data)
            results[name] = result
            print_analyst_status(name)
        except Exception as e:
            results[name] = {}
            print_analyst_status(name, "FAIL")
            print_error(f"{name} 分析失败: {e}")

        # 检查是否余额不足，提前终止
        summary = results[name].get("summary", "")
        if "余额不足" in summary or "充值" in summary:
            print_error("GLM API 余额不足，跳过后续 LLM 分析")
            # 为剩余 analyst 填充空结果
            remaining = [n for n, _, _ in analysts if n not in results]
            for n in remaining:
                results[n] = {}
            break

    return results


def phase3_score(analyst_reports: dict, raw_data: dict):
    """Phase 3: 研究主管汇总 + 热度评分"""
    print_phase("Phase 3", "研究主管汇总分析")

    from agents.research_lead import ResearchLead
    from agents.heat_scorer import HeatScorer

    # Research Lead 汇总
    lead = ResearchLead()
    research_data = lead.analyze(analyst_reports)
    print_analyst_status("Research Lead")

    # 构造评分所需原始数据
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

    # Heat Scorer 评分
    print_phase("Phase 3", "热度评分与排名")
    scorer = HeatScorer()
    report = scorer.analyze(research_data, raw_for_scorer)
    print_analyst_status("Heat Scorer")

    return report


def check_llm_available() -> bool:
    """预检 LLM API 是否可用"""
    from llm.glm_client import get_llm_client
    from output.console import print_info
    try:
        client = get_llm_client()
        client.quick_classify("回复OK", "你是API健康检查助手")
        print_info("GLM API 连接正常")
        return True
    except Exception as e:
        err = str(e)
        if "1113" in err or "余额不足" in err:
            print_error(f"GLM API 余额不足，请到 https://open.bigmodel.cn 充值后重试")
        else:
            print_error(f"GLM API 连接失败: {e}")
        return False


def main():
    """主入口"""
    setup_logging()
    print_header()

    try:
        settings = get_settings()
        universe = get_stock_universe()
    except Exception as e:
        print_error(f"配置加载失败: {e}")
        sys.exit(1)

    # 预检 LLM API
    llm_ok = check_llm_available()

    with ThreadPoolExecutor(max_workers=4) as executor:
        # Phase 1: 数据采集
        raw_data = phase1_fetch_data(executor)

    # 检查是否有数据
    total_items = sum(len(v) for v in raw_data.values())
    if total_items == 0:
        print_error("未获取到任何数据，请检查网络连接和API配置")
        sys.exit(1)

    if not llm_ok:
        print_error("跳过 LLM 分析（API不可用），仅保存原始数据")
        from models.heat_report import HeatReport
        report = HeatReport()
    else:
        # Phase 2: 数据分析（串行避免限流）
        analyst_reports = phase2_analyze(raw_data)

        # Phase 3: 汇总评分
        report = phase3_score(analyst_reports, raw_data)

    # 输出结果
    print_report(report)

    # 保存文件
    path = save_report(report)
    print_done(path)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n用户中断")
    except Exception as e:
        import traceback
        print_error(f"程序崩溃: {e}")
        traceback.print_exc()
        # 写入崩溃日志
        crash_log = ROOT / "logs" / "crash.log"
        crash_log.parent.mkdir(exist_ok=True)
        with open(crash_log, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n{datetime.now()}\n")
            traceback.print_exc(file=f)
    finally:
        input("按回车键退出...")
