"""GLM (智谱) API 客户端"""
import json
import logging
import os
import time
from typing import Optional

from zhipuai import ZhipuAI

logger = logging.getLogger(__name__)


class GLMClient:
    """智谱 GLM API 客户端"""

    def __init__(self, api_key: str, model_deep: str = "glm-4-plus", model_quick: str = "glm-4-flash",
                 max_retries: int = 3, timeout: int = 60):
        self._client = ZhipuAI(api_key=api_key)
        self._model_deep = model_deep
        self._model_quick = model_quick
        self._max_retries = max_retries
        self._timeout = timeout

    def chat(self, prompt: str, system: str = "", temperature: float = 0.7,
             use_deep: bool = True) -> str:
        """统一对话接口"""
        model = self._model_deep if use_deep else self._model_quick
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        for attempt in range(self._max_retries):
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    timeout=self._timeout,
                )
                return response.choices[0].message.content
            except Exception as e:
                err_msg = str(e)
                # 余额不足/无权限 → 快速失败，不重试
                if "1113" in err_msg or "余额不足" in err_msg:
                    raise
                logger.warning(f"LLM调用失败 (attempt {attempt + 1}/{self._max_retries}): {e}")
                if attempt < self._max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    raise

    def chat_json(self, prompt: str, system: str = "", temperature: float = 0.3,
                  use_deep: bool = False) -> dict:
        """对话并返回JSON格式结果"""
        system_msg = system + "\n请以JSON格式返回结果，不要包含其他文字。" if system else "请以JSON格式返回结果，不要包含其他文字。"
        text = self.chat(prompt, system_msg, temperature, use_deep)
        # 提取JSON
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1] if "\n" in text else text[3:]
            text = text.rsplit("```", 1)[0]
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            logger.error(f"JSON解析失败: {text[:200]}")
            return {}

    def quick_classify(self, prompt: str, system: str = "") -> str:
        """快速分类（使用 glm-4-flash）"""
        return self.chat(prompt, system, temperature=0.1, use_deep=False)

    def deep_analyze(self, prompt: str, system: str = "") -> str:
        """深度分析（使用 glm-4-plus）"""
        return self.chat(prompt, system, temperature=0.5, use_deep=True)


_client: GLMClient | None = None

def get_llm_client() -> GLMClient:
    global _client
    if _client is None:
        # 延迟导入避免循环依赖
        from config.settings import get_settings
        settings = get_settings()
        llm_cfg = settings.llm
        _client = GLMClient(
            api_key=llm_cfg.get("api_key", os.environ.get("ZHIPU_API_KEY", "")),
            model_deep=llm_cfg.get("model_deep", "glm-4-plus"),
            model_quick=llm_cfg.get("model_quick", "glm-4-flash"),
            max_retries=llm_cfg.get("max_retries", 3),
            timeout=llm_cfg.get("timeout", 60),
        )
    return _client
