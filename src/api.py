"""
src/api.py
----------
FastAPI application for KaushalSetu.
Provides:
  1. Live static serving of the KaushalSetu Dashboard (single origin, zero CORS hassle).
  2. REST API endpoints for pipeline status, triggering runs, and JSON dashboard data.
  3. Gemini AI narrative insight endpoints per skill & district.
  4. Server-side What-If policy simulation endpoint.
"""

import os
import sys
import json
import time
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Depends
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add current directory to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

import config
import m4_recommendation
import m6_curriculum_alignment
import m5_dashboard_data
import m7_ai_insights
from db import is_db_available, get_db
from models import PipelineRun

app = FastAPI(
    title="KaushalSetu API",
    description="Predictive Skill Demand & Training Recommendation Engine (SIH26134)",
    version="2.0.0"
)

# Enable CORS for local testing or external consumers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

TEMPLATE_PATH = os.path.join(BASE_DIR, "frontend", "dashboard_template.html")
COMPILED_HTML_PATH = os.path.join(BASE_DIR, "kaushalsetu-dashboard.html")

# In-memory status of pipeline execution
_PIPELINE_STATE = {
    "is_running": False,
    "last_run": None,
    "last_duration_seconds": 0.0,
    "status": "Ready",
    "error": None
}


class SimulateRequest(BaseModel):
    skill: str
    district: str
    additional_seats: int


# ------------------- HTML / DASHBOARD ROUTES -------------------

@app.get("/", response_class=HTMLResponse)
@app.get("/dashboard", response_class=HTMLResponse)
def get_dashboard():
    """Serves the dashboard HTML dynamically, reading fresh JSON."""
    if not os.path.exists(TEMPLATE_PATH):
        raise HTTPException(status_code=404, detail="Dashboard template not found.")

    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        html_content = f.read()

    # Load fresh dashboard data
    data = get_dashboard_data_payload()
    data_json = json.dumps(data)

    # Inject data into placeholder so the page works seamlessly on first load
    placeholder = "__KAUSHALSETU_DATA_PLACEHOLDER__"
    if placeholder in html_content:
        html_content = html_content.replace(placeholder, data_json)

    return HTMLResponse(content=html_content)


# ------------------- API ENDPOINTS -------------------

@app.get("/api/health")
def health_check():
    """Health check including DB connection and Gemini API status."""
    db_connected = is_db_available()
    gemini_configured = bool(os.getenv("GEMINI_API_KEY"))
    serpapi_configured = bool(os.getenv("SERPAPI_KEY"))

    return {
        "status": "ok",
        "service": "KaushalSetu Live Backend",
        "database_connected": db_connected,
        "gemini_configured": gemini_configured,
        "serpapi_configured": serpapi_configured,
        "pipeline_state": _PIPELINE_STATE,
        "timestamp": time.time()
    }


def get_dashboard_data_payload() -> dict:
    """Helper to get current dashboard data from file or rebuild."""
    if os.path.exists(config.OUT_DASHBOARD_DATA):
        try:
            with open(config.OUT_DASHBOARD_DATA, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    # If not yet generated, build in-memory
    return m5_dashboard_data.build()


@app.get("/api/dashboard-data")
def get_dashboard_data():
    """Returns the full aggregated JSON data structure for the frontend."""
    return get_dashboard_data_payload()


@app.get("/api/pipeline/status")
def get_pipeline_status():
    """Returns the latest status of data pipeline runs."""
    return _PIPELINE_STATE


def _execute_pipeline_task(force_trends: bool = False):
    global _PIPELINE_STATE
    start_time = time.time()
    _PIPELINE_STATE["is_running"] = True
    _PIPELINE_STATE["status"] = "Executing Pipeline"
    _PIPELINE_STATE["error"] = None

    try:
        # Run modules
        recommendations, district_summary = m4_recommendation.run()
        m6_curriculum_alignment.run()
        data = m5_dashboard_data.run()

        # Sync to Neon DB if configured
        try:
            from init_db import sync_csv_to_db
            sync_csv_to_db()
        except Exception as db_err:
            print(f"[API] DB sync skipped or failed: {db_err}")

        duration = round(time.time() - start_time, 2)
        _PIPELINE_STATE["is_running"] = False
        _PIPELINE_STATE["status"] = "Completed"
        _PIPELINE_STATE["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")
        _PIPELINE_STATE["last_duration_seconds"] = duration
        print(f"[API] Pipeline completed successfully in {duration}s")
    except Exception as e:
        _PIPELINE_STATE["is_running"] = False
        _PIPELINE_STATE["status"] = "Failed"
        _PIPELINE_STATE["error"] = str(e)
        print(f"[API] Pipeline failed: {e}")


@app.post("/api/pipeline/run")
def trigger_pipeline_run(background_tasks: BackgroundTasks, sync: bool = Query(False, description="Run synchronously if true")):
    """Triggers end-to-end execution of M1–M6 pipeline and syncs outputs."""
    if _PIPELINE_STATE["is_running"]:
        return JSONResponse(status_code=409, content={"message": "Pipeline is already running in background."})

    if sync:
        _execute_pipeline_task()
        return {"status": "success", "message": "Pipeline executed synchronously.", "details": _PIPELINE_STATE}
    else:
        background_tasks.add_task(_execute_pipeline_task)
        return {"status": "started", "message": "Pipeline run started in background."}


@app.get("/api/skills")
def list_skills():
    """Returns a list of all skills available in the dataset."""
    data = get_dashboard_data_payload()
    skills = [
        {
            "name": s["name"],
            "current_demand": s.get("current", 0),
            "predicted_12m": s.get("fut12", 0),
            "confidence": s.get("confidence", 50)
        }
        for s in data.get("forecast_skills", [])
    ]
    return {"skills": skills, "total": len(skills)}


@app.get("/api/skills/{skill}/insight")
def get_skill_ai_insight(skill: str, district: Optional[str] = Query(None)):
    """
    Returns explainable narrative generated by Google Gemini Flash
    based on the factual output produced by Modules 1-6.
    """
    data = get_dashboard_data_payload()
    forecast_item = next((s for s in data.get("forecast_skills", []) if s["name"].lower() == skill.lower()), None)
    gap_item = next((g for g in data.get("gap_list", []) if g["name"].lower() == skill.lower()), None)
    rec_item = next((r for r in data.get("other_recommendations", []) if r["skill"].lower() == skill.lower()), None)
    if not rec_item and data.get("recommendation", {}).get("skill", "").lower() == skill.lower():
        rec_item = data["recommendation"]

    if not forecast_item:
        raise HTTPException(status_code=404, detail=f"Skill '{skill}' not found in dataset.")

    # Assemble factual metrics for Gemini
    metrics = {
        "current_demand_score": forecast_item.get("current", 0),
        "predicted_score_12m": forecast_item.get("fut12", 0),
        "confidence_12m": forecast_item.get("confidence", 60),
        "gap_status": gap_item.get("status", "Balanced") if gap_item else "Balanced",
        "additional_seats": rec_item.get("seats", 0) if rec_item else 0,
        "additional_trainers": rec_item.get("trainers", 0) if rec_item else 0,
        "additional_labs": rec_item.get("labs", 0) if rec_item else 0,
        "curriculum_status": rec_item.get("curriculum_status", "Standard curriculum exists") if rec_item else "Standard curriculum",
        "district": district or (gap_item.get("district") if gap_item else "Maharashtra")
    }

    # Extract why-factors
    for factor in forecast_item.get("why", []):
        k, v, _ = factor
        if "growth rate" in k.lower():
            try:
                metrics["growth_rate_percent"] = float(v.replace("%", "").replace("+", ""))
            except Exception:
                pass
        elif "emerging" in k.lower():
            metrics["emerging_bonus"] = v
        elif "obsolescence" in k.lower():
            metrics["obsolescence_risk"] = v

    insight = m7_ai_insights.generate_skill_insight(
        skill_name=forecast_item["name"],
        metrics=metrics,
        district=district
    )
    return insight


@app.get("/api/districts/{district}/insight")
def get_district_ai_insight(district: str):
    """Returns AI workforce policy insight for a specific district."""
    data = get_dashboard_data_payload()
    dist_item = next((d for d in data.get("districts", []) if d["name"].lower() == district.lower()), None)

    if not dist_item:
        raise HTTPException(status_code=404, detail=f"District '{district}' not found.")

    summary = {
        "top_priority_skill": dist_item.get("topSkill", "Technical Skills"),
        "total_additional_seats": dist_item.get("gapSeats", 0),
        "total_additional_trainers": dist_item.get("trainers", 0),
        "total_additional_labs": dist_item.get("labs", 0),
        "skills_flagged": len(dist_item.get("priorities", []))
    }

    insight = m7_ai_insights.generate_district_insight(dist_item["name"], summary)
    return insight


@app.post("/api/simulate")
def run_simulation(req: SimulateRequest):
    """
    Server-side What-If policy simulation.
    Recalculates labor gap status and trainer/lab requirements given additional seats.
    """
    data = get_dashboard_data_payload()
    matching_gap = next((g for g in data.get("gap_list", [])
                        if g["name"].lower() == req.skill.lower() and
                           g["district"].lower() == req.district.lower()), None)

    if not matching_gap:
        demand = 100
        current_supply = 20
    else:
        demand = matching_gap["demand"]
        current_supply = matching_gap["supply"]

    new_supply = current_supply + req.additional_seats
    gap_after = max(demand - new_supply, 0)
    ratio = demand / max(new_supply, 1)

    if ratio >= config.GAP_CRITICAL_RATIO:
        status = "Critical Shortage"
        status_class = "critical"
    elif ratio >= config.GAP_SHORTAGE_RATIO:
        status = "Shortage"
        status_class = "shortage"
    elif ratio <= config.GAP_OVERSUPPLY_RATIO:
        status = "Oversupply"
        status_class = "over"
    else:
        status = "Balanced"
        status_class = "balanced"

    extra_trainers = max(1, round(req.additional_seats / config.SEATS_PER_TRAINER)) if req.additional_seats > 0 else 0
    extra_labs = max(1, round(req.additional_seats / config.SEATS_PER_LAB)) if req.additional_seats > 0 else 0

    return {
        "skill": req.skill,
        "district": req.district,
        "seats_added": req.additional_seats,
        "demand": demand,
        "initial_supply": current_supply,
        "projected_supply": new_supply,
        "gap_before": max(demand - current_supply, 0),
        "gap_after": gap_after,
        "status": status,
        "status_class": status_class,
        "trainers_needed": extra_trainers,
        "labs_needed": extra_labs
    }
