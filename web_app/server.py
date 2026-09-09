"""FastAPI Application Server for Enterprise Digital Twin.

Exposes REST APIs for:
1. Executive Dashboard KPIs & Visualizations.
2. Financial Reporting Center (P&L, Cash Flow, Category Margins).
3. Crisis Incident Command & Root Cause Analysis (RCA).
4. Natural Language AI Assistant (NL2SQL & Business Synthesizer).
5. Serves modern static web frontend.
"""

import sys
import queue
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from web_app.services.financial_engine import FinancialEngine
from web_app.services.dashboard_service import DashboardService
from web_app.services.nl_query_engine import NLQueryEngine
from web_app.services.background_worker import sentinel_worker
from web_app.services.streaming_engine import stream_engine
from web_app.services.enterprise_analytics_engine import EnterpriseAnalyticsEngine
from ai_analyst.orchestrator import MultiAgentOrchestrator
from web_app.services.action_actuator import action_actuator


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manages application lifecycle: Autonomous Sentinel Daemon & Live Stream Ingestion Engine."""
    print("[Server Lifespan] Starting 24/7 Autonomous Sentinel Worker...")
    sentinel_worker.start()
    print("[Server Lifespan] Starting Continuous Event Stream Ingestion Engine...")
    stream_engine.start()
    yield
    print("[Server Lifespan] Stopping Continuous Event Stream Ingestion Engine...")
    stream_engine.stop()
    print("[Server Lifespan] Stopping 24/7 Autonomous Sentinel Worker...")
    sentinel_worker.stop()


app = FastAPI(
    title="Enterprise Digital Twin Platform",
    description="Executive Command, Financial Intelligence & AI Analyst Engine",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS for development flexibility
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

nl_engine = NLQueryEngine()
STATIC_DIR = Path(__file__).resolve().parent / "static"


class AIQueryRequest(BaseModel):
    query: str


class WhatIfSimulationRequest(BaseModel):
    backup_supplier_active: Optional[bool] = True
    ghn_reroute_pct: Optional[float] = 35.0
    momo_failover: Optional[bool] = True
    tiktok_realloc_pct: Optional[float] = 50.0
    eco_ota_patch: Optional[bool] = True


class ActionExecuteRequest(BaseModel):
    action_id: str
    approved_by: Optional[str] = "HumanOperator"


# =============================================================================
# Dashboard API Endpoints
# =============================================================================

@app.get("/api/dashboard/overview")
def get_dashboard_overview(
    timeframe: Optional[str] = Query("all", description="Timeframe: all | pre_crisis | peak_crisis | recovery")
):
    """Returns executive health index, operational alerts, KPIs, trends, channel performance, and carrier SLAs."""
    try:
        health = DashboardService.get_executive_health_index()
        alerts = DashboardService.get_operational_alerts(timeframe=timeframe)
        kpis = DashboardService.get_executive_kpis(timeframe=timeframe)
        trends = DashboardService.get_revenue_trends(timeframe=timeframe)
        channels = DashboardService.get_channel_breakdown()
        carriers = DashboardService.get_carrier_performance()
        incidents = DashboardService.get_incident_monitor()

        return {
            "status": "SUCCESS",
            "timestamp": datetime.now().isoformat(),
            "timeframe": timeframe,
            "health": health,
            "alerts": alerts,
            "kpis": kpis,
            "trends": trends,
            "channels": channels,
            "carriers": carriers,
            "incidents": incidents,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/supply-chain")
def get_supply_chain_data():
    """Returns warehouses capacity, critical low-stock SKUs, and supplier performance."""
    try:
        data = DashboardService.get_supply_chain_inventory()
        return {
            "status": "SUCCESS",
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/dashboard/customer-marketing")
def get_customer_marketing_data():
    """Returns CRM customer segments, sentiment ratings, support tickets, and marketing CAC/ROAS."""
    try:
        data = DashboardService.get_customer_marketing_intelligence()
        return {
            "status": "SUCCESS",
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/simulation/causal-dag")
def get_causal_dag_data():
    """Returns structured Causal DAG nodes and relations for S001-S005."""
    try:
        dags = DashboardService.get_causal_dag_models()
        return {
            "status": "SUCCESS",
            "dags": dags,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/simulation/what-if")
def run_what_if_simulation(req: WhatIfSimulationRequest):
    """Calculates quantitative recovery impact based on digital twin interventions."""
    try:
        result = DashboardService.simulate_interventions(req.model_dump())
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/simulation/agent-debate")
def get_agent_debate(
    scenario: Optional[str] = Query("S001", description="Scenario code (S001-S005)"),
):
    """Returns the Multi-Agent Debate Arena data including agent scorecards, rounds, and accountability verdicts."""
    try:
        data = DashboardService.get_agent_debate_arena(scenario)
        return {
            "status": "SUCCESS",
            "scenario": scenario,
            "data": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/simulation/pro-agent-audit")
def get_pro_agent_audit():
    """Runs the 6-Agent PRO Enterprise Strategic Audit with adversarial critique and accountability tracking."""
    try:
        orch = MultiAgentOrchestrator()
        result = orch.run_pro_enterprise_audit()
        return {
            "status": "SUCCESS",
            "data": result,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Closed-Loop Autonomous Action & Intervention Endpoints (Bậc 3 & Bậc 4)
# =============================================================================

@app.get("/api/actions/proposals")
def get_action_proposals():
    """Returns AI 6-Agent certified intervention action proposals."""
    try:
        data = action_actuator.generate_pro_action_proposals()
        return data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/actions/execute")
def execute_action_proposal(req: ActionExecuteRequest):
    """Executes an approved action proposal transactionally into PostgreSQL."""
    try:
        res = action_actuator.execute_action(
            action_id=req.action_id,
            approved_by=req.approved_by or "HumanOperator",
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/actions/history")
def get_action_history():
    """Returns full execution audit history for closed-loop interventions."""
    try:
        history = action_actuator.get_action_audit_history()
        return {
            "status": "SUCCESS",
            "total_executed_actions": len(history),
            "history": history,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Multi-Dimensional Analytics API Endpoints (Bậc 1 & Bậc 2)
# =============================================================================

@app.get("/api/analytics/temporal")
def get_analytics_temporal(
    grain: Optional[str] = Query("month", description="Time aggregation grain: month | quarter")
):
    """Returns multi-temporal time-series analysis (MoM, QoQ, YoY) from 2025 to 2026."""
    try:
        data = EnterpriseAnalyticsEngine.get_temporal_growth_analysis(grain=grain)
        return {
            "status": "SUCCESS",
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/comparative")
def get_analytics_comparative():
    """Returns cross-dimensional benchmarking matrix across Channels, Stores, Carriers, Payments, and Suppliers."""
    try:
        data = EnterpriseAnalyticsEngine.get_comparative_matrix()
        return {
            "status": "SUCCESS",
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/diagnostic")
def get_analytics_diagnostic():
    """Returns Bậc 2 root-cause decomposition, Z-score anomaly tests, and financial loss attribution."""
    try:
        data = EnterpriseAnalyticsEngine.get_diagnostic_deep_dive()
        return {
            "status": "SUCCESS",
            "timestamp": datetime.now().isoformat(),
            "data": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/analytics/summary")
def get_analytics_summary():
    """Returns executive synthesized summary combining Bậc 1 & Bậc 2 for C-Level decision making."""
    try:
        data = EnterpriseAnalyticsEngine.get_executive_summary_report()
        return {
            "status": "SUCCESS",
            "timestamp": datetime.now().isoformat(),
            "report": data,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Financial Center API Endpoints
# =============================================================================

@app.get("/api/finance/pnl")
def get_pnl(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
):
    """Computes comprehensive P&L statement with incident loss attribution."""
    try:
        st = datetime.fromisoformat(start_date) if start_date else None
        et = datetime.fromisoformat(end_date) if end_date else None
        pnl = FinancialEngine.get_pnl_statement(st, et)
        return {
            "status": "SUCCESS",
            "pnl": pnl,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/finance/cashflow")
def get_cash_flow():
    """Computes direct cash flow statement (inflows vs outflows)."""
    try:
        cf = FinancialEngine.get_cash_flow_statement()
        return {
            "status": "SUCCESS",
            "cash_flow": cf,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/finance/categories")
def get_categories_margin():
    """Returns profitability and margin rate by product category."""
    try:
        cats = FinancialEngine.get_category_profitability()
        return {
            "status": "SUCCESS",
            "categories": cats,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Crisis Incidents & RCA API Endpoints
# =============================================================================

@app.get("/api/incidents")
def get_incidents():
    """Returns all active crisis incidents with their details and RCA reports."""
    try:
        incidents = DashboardService.get_incident_monitor()
        return {
            "status": "SUCCESS",
            "incidents": incidents,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class SentinelConfigPayload(BaseModel):
    interval_seconds: int


# =============================================================================
# Autonomous 24/7 Sentinel API Endpoints
# =============================================================================

@app.get("/api/sentinel/status")
def get_sentinel_status():
    """Returns 24/7 autonomous monitoring status and operational telemetry."""
    try:
        return {
            "status": "SUCCESS",
            "telemetry": sentinel_worker.get_status(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sentinel/toggle")
def toggle_sentinel():
    """Toggles active/paused state of autonomous heartbeat monitoring."""
    try:
        is_active = sentinel_worker.toggle()
        return {
            "status": "SUCCESS",
            "is_active": is_active,
            "message": "Chế độ giám sát tự trị 24/7: " + ("ĐANG HOẠT ĐỘNG" if is_active else "ĐÃ TẠM DỪNG"),
            "telemetry": sentinel_worker.get_status(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sentinel/scan-now")
def trigger_sentinel_scan(
    force_rca: Optional[bool] = Query(False, description="Force re-dispatch RCA investigation even if report exists")
):
    """Executes on-demand instant operational scan and auto-dispatches AI analysts."""
    try:
        result = sentinel_worker.scan_now(force_rca=force_rca)
        return {
            "status": "SUCCESS",
            "message": "Đã hoàn thành vòng quét nhịp tim doanh nghiệp tức thời.",
            "scan_result": result,
            "telemetry": sentinel_worker.get_status(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/sentinel/config")
def update_sentinel_config(payload: SentinelConfigPayload):
    """Updates scan frequency interval in seconds."""
    try:
        sentinel_worker.set_interval(payload.interval_seconds)
        return {
            "status": "SUCCESS",
            "message": f"Đã cập nhật chu kỳ quét: {payload.interval_seconds} giây.",
            "telemetry": sentinel_worker.get_status(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/sentinel/logs")
def get_sentinel_logs(limit: Optional[int] = Query(50, ge=1, le=200)):
    """Returns audit log trail of autonomous heartbeat scans and dispatches."""
    try:
        logs = sentinel_worker.get_logs(limit=limit)
        return {
            "status": "SUCCESS",
            "total_logs": len(logs),
            "logs": logs,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Continuous Data Streaming & Continual Learning Endpoints
# =============================================================================

class StreamInjectPayload(BaseModel):
    domain: Optional[str] = "Sales & Revenue"
    event_type: Optional[str] = "CHECKOUT_COMPLETED"
    summary: str
    details: Optional[Dict[str, Any]] = None


class StreamConfigPayload(BaseModel):
    speed_multiplier: Optional[float] = 1.0
    burst_mode: Optional[bool] = False


class ChaosInjectPayload(BaseModel):
    chaos_type: str
    severity: Optional[float] = 0.8
    duration_seconds: Optional[int] = 180


class InterventionPayload(BaseModel):
    action: str
    parameters: Optional[Dict[str, Any]] = None


@app.get("/api/stream/status")
def get_stream_status():
    """Returns real-time event streaming telemetry and continual learning moving baselines."""
    try:
        return {
            "status": "SUCCESS",
            "stream": stream_engine.get_status(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stream/events/sse")
async def stream_events_sse():
    """Server-Sent Events (SSE) full-duplex live event stream (<50ms)."""
    import asyncio
    q = stream_engine.subscribe_sse()

    async def event_generator():
        try:
            while True:
                try:
                    raw_event = q.get_nowait()
                    yield raw_event
                except queue.Empty:
                    await asyncio.sleep(0.08)
        except asyncio.CancelledError:
            stream_engine.unsubscribe_sse(q)
        finally:
            stream_engine.unsubscribe_sse(q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/stream/config")
def update_stream_config(payload: StreamConfigPayload):
    """Sets simulation speed multiplier (1x, 10x, 60x) or burst mode."""
    try:
        stream_engine.set_speed(multiplier=payload.speed_multiplier or 1.0, burst=bool(payload.burst_mode))
        return {
            "status": "SUCCESS",
            "message": f"Tốc độ luồng: {payload.speed_multiplier}x (Burst: {payload.burst_mode})",
            "stream": stream_engine.get_status(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stream/chaos/inject")
def inject_chaos_event(payload: ChaosInjectPayload):
    """Injects dynamic chaos condition into operational stream (surface symptoms only, zero-leakage)."""
    try:
        chaos_res = stream_engine.inject_chaos(
            chaos_type=payload.chaos_type,
            severity=payload.severity or 0.8,
            duration_seconds=payload.duration_seconds or 180,
        )
        return {
            "status": "SUCCESS",
            "message": f"Đã kích hoạt sự cố động: {payload.chaos_type} (Mức độ: {payload.severity})",
            "chaos": chaos_res,
            "stream": stream_engine.get_status(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/twin/intervene")
def execute_twin_intervention(payload: InterventionPayload):
    """Executes closed-loop digital twin self-healing intervention via policy guardrail."""
    try:
        res = stream_engine.execute_intervention(
            action=payload.action,
            parameters=payload.parameters,
        )
        return {
            "status": res.get("status", "SUCCESS"),
            "intervention": res,
            "stream": stream_engine.get_status(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stream/toggle")
def toggle_stream():
    """Toggles active/paused state of continuous event streaming pipeline."""
    try:
        is_active = stream_engine.toggle()
        return {
            "status": "SUCCESS",
            "is_active": is_active,
            "message": "Luồng dữ liệu thời gian thực (Live Stream): " + ("ĐANG CHẢY LIÊN TỤC" if is_active else "ĐÃ TẠM DỪNG"),
            "stream": stream_engine.get_status(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/stream/inject")
def inject_stream_event(payload: StreamInjectPayload):
    """Manually injects an operational event and recalculates model moving baselines."""
    try:
        record = stream_engine.inject_event(
            domain=payload.domain or "Sales & Revenue",
            event_type=payload.event_type or "MANUAL_EVENT",
            summary=payload.summary,
            details=payload.details or {},
        )
        return {
            "status": "SUCCESS",
            "message": "Đã bơm sự kiện vào luồng dữ liệu và hiệu chỉnh đường cơ sở AI.",
            "event": record,
            "stream": stream_engine.get_status(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Natural Language AI Assistant API Endpoints
# =============================================================================

@app.post("/api/ai/query")
def process_ai_query(req: AIQueryRequest):
    """Processes natural language query using AI Query Engine in sandbox."""
    if not req.query or not req.query.strip():
        raise HTTPException(status_code=400, detail="Query string cannot be empty.")

    try:
        result = nl_engine.process_query(req.query)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


from web_app.services.nl_query_engine import NLQueryEngine, AIConfigManager

class AIConfigPayload(BaseModel):
    provider: str
    api_key: str
    model: Optional[str] = None


@app.get("/api/ai/config")
def get_ai_config():
    """Returns current AI Engine configuration status."""
    cfg = AIConfigManager.load_config()
    provider = cfg.get("provider", "gemini")
    key = cfg.get(f"{provider}_api_key", "").strip()
    masked = f"{key[:4]}...{key[-4:]}" if len(key) >= 8 else ("***" if key else "")
    return {
        "status": "SUCCESS",
        "provider": provider,
        "model": cfg.get(f"{provider}_model", "gemini-2.0-flash"),
        "has_api_key": bool(key),
        "masked_key": masked,
        "mode": f"LLM ({provider.title()})" if key else "Universal Semantic Engine (Offline)",
    }


@app.post("/api/ai/config")
def save_ai_config(payload: AIConfigPayload):
    """Saves AI Engine configuration and verifies connection."""
    prov = payload.provider.lower().strip()
    key = payload.api_key.strip()
    model = payload.model.strip() if payload.model else ("gemini-2.0-flash" if prov == "gemini" else "gpt-4o-mini")

    if key:
        ok, msg = AIConfigManager.test_connection(prov, key, model)
        if not ok:
            raise HTTPException(status_code=400, detail=f"Xác thực thất bại: {msg}")

    update_dict = {
        "provider": prov,
        f"{prov}_api_key": key,
        f"{prov}_model": model,
    }
    AIConfigManager.save_config(update_dict)
    return {
        "status": "SUCCESS",
        "message": f"Đã lưu cấu hình {prov.title()} ({model}) thành công!",
    }


@app.post("/api/ai/test-connection")
def test_ai_connection(payload: AIConfigPayload):
    """Tests LLM connection without saving."""
    prov = payload.provider.lower().strip()
    key = payload.api_key.strip()
    model = payload.model.strip() if payload.model else ("gemini-2.0-flash" if prov == "gemini" else "gpt-4o-mini")
    ok, msg = AIConfigManager.test_connection(prov, key, model)
    return {"success": ok, "message": msg}


@app.get("/api/ai/suggestions")
def get_ai_suggestions():
    """Returns curated high-value executive questions."""
    return {
        "suggestions": [
            "Báo cáo kết quả hoạt động kinh doanh (P&L) toàn diện",
            "Tại sao lợi nhuận MoMo giảm trong ngày 15/08/2026?",
            "Đơn vị vận chuyển nào có tỷ lệ giao trễ cao nhất và chi phí bồi hoàn là bao nhiêu?",
            "Hiệu quả chiến dịch TikTok so với các kênh khác (CAC & CVR)?",
            "Ai là khách hàng có tổng giá trị mua hàng cao nhất?",
            "Lý do phổ biến nhất trong các đánh giá 1 sao của khách hàng?",
            "Danh sách các đơn hàng có giá trị trên 50 triệu VND?",
            "Tổng thiệt hại tài chính từ 5 sự cố khủng hoảng (S001-S005)?",
            "Có bao nhiêu kho và lượng hàng tồn kho khả dụng hiện tại?",
        ]
    }


# =============================================================================
# Frontend Static Files Mount
# =============================================================================

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def serve_index():
    """Serves the main single-page web application."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        return JSONResponse(
            status_code=404,
            content={"message": "Frontend index.html is being prepared."},
        )
    return FileResponse(index_file)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("web_app.server:app", host="0.0.0.0", port=8000, reload=True)
