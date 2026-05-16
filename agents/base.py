"""Agent 基类"""
import logging
from abc import ABC, abstractmethod
from typing import Any

from llm.glm_client import GLMClient, get_llm_client


class BaseAgent(ABC):
    """Agent 抽象基类"""

    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(f"agent.{name}")
        self._llm: GLMClient | None = None

    @property
    def llm(self) -> GLMClient:
        if self._llm is None:
            self._llm = get_llm_client()
        return self._llm

    @abstractmethod
    def analyze(self, data: Any) -> Any:
        """分析数据并返回结果"""
        ...

    def _truncate_text(self, text: str, max_chars: int = 8000) -> str:
        """截断过长文本"""
        if len(text) > max_chars:
            return text[:max_chars] + f"\n... (已截断，原文 {len(text)} 字符)"
        return text
