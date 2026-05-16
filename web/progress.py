"""全局状态管理 + SSE 事件分发"""
import json
import queue
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional


class PipelineStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class PipelineState:
    """流水线状态（单例，线程安全）"""
    status: PipelineStatus = PipelineStatus.IDLE
    current_phase: str = ""
    raw_data: dict = field(default_factory=dict)
    analyst_reports: dict = field(default_factory=dict)
    report: Any = None  # HeatReport
    error_message: str = ""
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

    # 各组件状态: name -> "pending" | "running" | "done" | "fail"
    fetcher_status: dict = field(default_factory=dict)
    analyst_status: dict = field(default_factory=dict)

    # 实时日志
    logs: list = field(default_factory=list)


class SSEManager:
    """SSE 客户端管理器"""

    def __init__(self):
        self._clients: list[queue.Queue] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue:
        q = queue.Queue(maxsize=200)
        with self._lock:
            self._clients.append(q)
        return q

    def unsubscribe(self, q: queue.Queue):
        with self._lock:
            if q in self._clients:
                self._clients.remove(q)

    def emit(self, event: str, data: dict):
        """广播事件到所有 SSE 客户端"""
        payload = json.dumps({"event": event, "data": data}, ensure_ascii=False, default=str)
        dead = []
        with self._lock:
            for q in self._clients:
                try:
                    q.put_nowait(payload)
                except queue.Full:
                    dead.append(q)
            for q in dead:
                self._clients.remove(q)


# --- 全局单例 ---
_state = PipelineState()
_state_lock = threading.Lock()
_sse_manager = SSEManager()


def get_state() -> PipelineState:
    return _state


def get_sse_manager() -> SSEManager:
    return _sse_manager


def reset_state():
    """重置状态（新一轮运行前调用）"""
    with _state_lock:
        _state.status = PipelineStatus.IDLE
        _state.current_phase = ""
        _state.raw_data = {}
        _state.analyst_reports = {}
        _state.report = None
        _state.error_message = ""
        _state.started_at = None
        _state.finished_at = None
        _state.fetcher_status = {
            "us_news": "pending",
            "cn_news": "pending",
            "cn_orders": "pending",
            "sentiment": "pending",
        }
        _state.analyst_status = {
            "sentiment": "pending",
            "us_news": "pending",
            "cn_news": "pending",
            "orders": "pending",
            "research_lead": "pending",
            "heat_scorer": "pending",
        }
        _state.logs = []


def emit(event: str, data: dict):
    """发送 SSE 事件并记录日志"""
    _sse_manager.emit(event, data)
    if event in ("log", "pipeline_error"):
        with _state_lock:
            _state.logs.append({
                "time": time.strftime("%H:%M:%S"),
                "event": event,
                "data": data,
            })
