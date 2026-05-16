"""报告文件保存"""
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent


def save_report(report) -> Path:
    """保存报告到 reports/ 目录，返回文件路径"""
    reports_dir = ROOT / "reports"
    reports_dir.mkdir(exist_ok=True)

    filename = f"heat_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = reports_dir / filename

    data = report.model_dump(mode="json")
    # 将 datetime 对象转为字符串
    if "generated_at" in data and isinstance(data["generated_at"], datetime):
        data["generated_at"] = data["generated_at"].isoformat()

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2, default=str)

    return filepath
