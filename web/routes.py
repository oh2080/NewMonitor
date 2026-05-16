"""路由定义: 页面 + API + SSE"""
import json
import queue
import threading

from flask import Blueprint, Response, jsonify, render_template, request

from web.pipeline_service import PipelineService
from web.progress import (
    PipelineStatus, get_sse_manager, get_state, reset_state,
)

bp = Blueprint("main", __name__)

# 后台任务线程引用
_run_thread: threading.Thread | None = None
_run_lock = threading.Lock()


# --- 页面 ---

@bp.get("/")
def index():
    return render_template("index.html")


# --- API ---

@bp.post("/api/run")
def api_run():
    """启动流水线（后台线程）"""
    state = get_state()

    with _run_lock:
        if state.status == PipelineStatus.RUNNING:
            return jsonify({"error": "流水线正在运行中"}), 409

    def _run():
        svc = PipelineService()
        svc.run()

    t = threading.Thread(target=_run, daemon=True)
    t.start()

    return jsonify({"message": "流水线已启动"})


@bp.get("/api/status")
def api_status():
    """查询当前状态"""
    state = get_state()
    elapsed = None
    if state.started_at:
        import time
        end = state.finished_at or time.time()
        elapsed = round(end - state.started_at, 1)

    return jsonify({
        "status": state.status.value,
        "current_phase": state.current_phase,
        "elapsed": elapsed,
        "fetcher_status": state.fetcher_status,
        "analyst_status": state.analyst_status,
        "error_message": state.error_message,
    })


@bp.get("/api/report")
def api_report():
    """获取最终报告 JSON"""
    state = get_state()
    if state.report is None:
        return jsonify({"error": "报告尚未生成"}), 404

    data = state.report.model_dump(mode="json")
    return jsonify(data)


@bp.get("/api/raw-data")
def api_raw_data():
    """获取原始采集数据 JSON"""
    state = get_state()
    if not state.raw_data:
        return jsonify({"error": "暂无数据"}), 404

    result = {}
    for source, items in state.raw_data.items():
        result[source] = [
            item.model_dump(mode="json") if hasattr(item, "model_dump") else item
            for item in items
        ]
    return jsonify(result)


# --- SSE ---

@bp.get("/api/stream")
def api_stream():
    """SSE 实时事件流"""
    sse = get_sse_manager()
    q = sse.subscribe()

    def generate():
        try:
            while True:
                try:
                    payload = q.get(timeout=30)
                    yield f"data: {payload}\n\n"
                except queue.Empty:
                    # 心跳
                    yield ": heartbeat\n\n"
        finally:
            sse.unsubscribe(q)

    response = Response(generate(), mimetype="text/event-stream")
    response.headers["Cache-Control"] = "no-cache"
    response.headers["X-Accel-Buffering"] = "no"
    return response
