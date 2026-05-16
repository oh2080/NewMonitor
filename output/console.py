"""终端输出函数（基于 rich 库）"""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

console = Console()


def print_header():
    """打印系统标题"""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]NewsMonitor - AI 热点股票监控系统[/bold cyan]\n"
        "[dim]数据采集 → LLM 分析 → 热度评分[/dim]",
        border_style="cyan",
    ))
    console.print()


def print_phase(phase: str, desc: str):
    """打印阶段标题"""
    console.print()
    console.rule(f"[bold yellow]{phase}: {desc}[/bold yellow]")
    console.print()


def print_fetcher_status(name: str, count: int, status: str = "OK"):
    """打印数据源采集状态"""
    label = _fetcher_label(name)
    if status == "OK":
        console.print(f"  [green]✓[/green] {label}: {count} 条数据")
    else:
        console.print(f"  [red]✗[/red] {label}: 采集失败")


def print_analyst_status(name: str, status: str = "OK"):
    """打印分析师状态"""
    label = _analyst_label(name)
    if status == "OK":
        console.print(f"  [green]✓[/green] {label}: 分析完成")
    else:
        console.print(f"  [red]✗[/red] {label}: 分析失败")


def print_report(report):
    """打印热度报告"""
    console.print()
    console.rule("[bold green]热度报告[/bold green]")

    if not report.ranked_stocks:
        console.print("[dim]无排名数据[/dim]")
        return

    table = Table(show_lines=True)
    table.add_column("排名", style="bold", width=4)
    table.add_column("代码", width=10)
    table.add_column("名称", width=12)
    table.add_column("市场", width=8)
    table.add_column("热度分", justify="right", width=8)
    table.add_column("新闻频率", justify="right", width=8)
    table.add_column("情绪", justify="right", width=8)
    table.add_column("订单信号", justify="right", width=8)
    table.add_column("LLM调整", justify="right", width=8)

    for i, stock in enumerate(report.ranked_stocks, 1):
        score_color = "red" if stock.heat_score >= 70 else "yellow" if stock.heat_score >= 40 else "green"
        table.add_row(
            str(i),
            stock.ticker,
            stock.name,
            stock.market,
            f"[{score_color}]{stock.heat_score:.1f}[/{score_color}]",
            f"{stock.news_frequency_score:.1f}",
            f"{stock.sentiment_score:.1f}",
            f"{stock.order_signal_score:.1f}",
            f"{stock.llm_adjustment:+.1f}",
        )

    console.print(table)

    if report.cross_market_insight:
        console.print()
        console.print(Panel(report.cross_market_insight, title="跨市场分析", border_style="blue"))

    if report.keywords:
        console.print()
        console.print(f"[bold]热门关键词:[/bold] {', '.join(report.keywords)}")

    if report.hidden_opportunities:
        console.print()
        console.print("[bold]隐藏机会:[/bold]")
        for opp in report.hidden_opportunities:
            console.print(f"  • {opp}")


def print_error(msg: str):
    """打印错误信息"""
    console.print(f"[bold red]错误:[/bold red] {msg}")


def print_done(path=None):
    """打印完成信息"""
    console.print()
    if path:
        console.print(f"[bold green]报告已保存:[/bold green] {path}")
    console.print("[bold green]完成！[/bold green]")


def print_info(msg: str):
    """打印提示信息"""
    console.print(f"[cyan]ℹ[/cyan] {msg}")


# --- 内部辅助 ---

_FETCHER_LABELS = {
    "us_news": "美股新闻",
    "cn_news": "A股新闻",
    "cn_orders": "公司公告/订单",
    "sentiment": "市场情绪",
}

_ANALYST_LABELS = {
    "sentiment": "情绪分析师",
    "us_news": "美股分析师",
    "cn_news": "A股分析师",
    "orders": "订单分析师",
    "Research Lead": "研究主管",
    "Heat Scorer": "评分引擎",
}


def _fetcher_label(name: str) -> str:
    return _FETCHER_LABELS.get(name, name)


def _analyst_label(name: str) -> str:
    return _ANALYST_LABELS.get(name, name)
