"""配置管理模块"""
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv


class Settings:
    """全局配置管理"""

    def __init__(self):
        self._root = Path(__file__).parent.parent
        load_dotenv(self._root / ".env")
        self._config = self._load_config()

    def _load_config(self) -> dict:
        config_path = self._root / "config.yaml"
        with open(config_path, "r", encoding="utf-8") as f:
            raw = f.read()
        # 替换环境变量
        import re
        def _replace_env(match):
            key = match.group(1)
            val = os.environ.get(key, "")
            return val
        raw = re.sub(r'\$\{(\w+)\}', _replace_env, raw)
        return yaml.safe_load(raw)

    @property
    def llm(self) -> dict:
        return self._config.get("llm", {})

    @property
    def scoring_weights(self) -> dict:
        return self._config.get("scoring", {}).get("weights", {})

    @property
    def data_sources(self) -> dict:
        return self._config.get("data_sources", {})

    @property
    def stock_universe_raw(self) -> dict:
        return self._config.get("stock_universe", {})

    @property
    def root(self) -> Path:
        return self._root


_settings: Settings | None = None

def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
