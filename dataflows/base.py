"""数据采集基类"""
import json
import logging
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import List

from models.news_item import NewsItem


class BaseFetcher(ABC):
    """数据采集抽象基类"""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"fetcher.{name}")

    @abstractmethod
    def fetch(self) -> List[NewsItem]:
        """执行数据采集，返回新闻列表"""
        ...

    def _cache_path(self) -> Path:
        """获取缓存文件路径"""
        from config.settings import get_settings
        cache_dir = get_settings().root / "cache"
        cache_dir.mkdir(exist_ok=True)
        return cache_dir / f"{self.name}_{date.today().isoformat()}.json"

    def _save_cache(self, items: List[NewsItem]):
        """保存缓存"""
        path = self._cache_path()
        data = [item.model_dump(mode="json") for item in items]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
        self.logger.info(f"缓存已保存: {path} ({len(items)}条)")

    def _load_cache(self) -> List[NewsItem] | None:
        """加载缓存"""
        path = self._cache_path()
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            items = [NewsItem(**d) for d in data]
            self.logger.info(f"从缓存加载: {path} ({len(items)}条)")
            return items
        return None
