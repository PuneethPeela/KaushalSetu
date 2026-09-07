"""
src/m7_ai_insights.py
---------------------
Gemini AI narrative insight module for KaushalSetu.
Provides explainable, natural language summaries and actionable recommendations
based exclusively on the pre-computed pipeline metrics.

Constraints respected:
  1. Uses the official google-genai SDK (not raw HTTP or deprecated libraries).
  2. Free-tier model family (gemini-2.5-flash / gemini-1.5-flash).
  3. Never fabricates numbers — strictly narrates already computed signals.
  4. Implements retry with exponential backoff and jitter on HTTP 429.
  5. Caching layer (in database or memory) keyed by (skill, district, gap_status, horizon).
  6. Graceful degradation: returns structured deterministic fallback when API key is unset or unavailable.
"""

import os
import json
import time
import random
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("kaushalsetu.ai")

# In-memory cache fallback: { cache_key: { "narrative": str, "timestamp": float } }
_MEMORY_CACHE: Dict[str, Dict[str, Any]] = {}
CACHE_TTL_SECONDS = 86400  # 24 hours

def _get_gemini_client():
    api_key = os.getenv("GEMINI_API_KEY", "").strip()
    if not api_key:
        return None
    try:
        from google import genai
        return genai.Client(api_key=api_key)
    except Exception as e:
        logger.warning(f"[m7_ai_insights] Could not initialize google-genai client: {e}")
        return None


def get_cached_insight(cache_key: str) -> Optional[Dict[str, Any]]:
    """Check Neon DB or in-memory cache for an existing insight."""
    # 1. Try in-memory cache
    if cache_key in _MEMORY_CACHE:
        entry = _MEMORY_CACHE[cache_key]
        if time.time() - entry.get("timestamp", 0) < CACHE_TTL_SECONDS:
            return entry.get("data")

    # 2. Try database cache if available
    try:
        from db import SessionLocal
        from models import AIInsightCache
        if SessionLocal:
            session = SessionLocal()
            try:
                row = session.query(AIInsightCache).filter_by(cache_key=cache_key).first()
                if row:
                    data = {
                        "narrative": row.narrative,
                        "recommendations_summary": row.recommendations_summary,
                        "model_used": row.model_used,
                        "is_fallback": row.is_fallback,
                        "source": "database_cache"
                    }
                    _MEMORY_CACHE[cache_key] = {"data": data, "timestamp": time.time()}
                    return data
            finally:
                session.close()
    except Exception:
        pass

    return None


def store_cached_insight(cache_key: str, data: Dict[str, Any], insight_type: str = "skill"):
    """Store generated insight into in-memory and database cache."""
    _MEMORY_CACHE[cache_key] = {"data": data, "timestamp": time.time()}

    try:
        from db import SessionLocal
        from models import AIInsightCache
        if SessionLocal:
            session = SessionLocal()
            try:
                existing = session.query(AIInsightCache).filter_by(cache_key=cache_key).first()
                if not existing:
                    new_entry = AIInsightCache(
                        cache_key=cache_key,
                        insight_type=insight_type,
                        narrative=data.get("narrative", ""),
                        recommendations_summary=data.get("recommendations_summary", ""),
                        model_used=data.get("model_used", "gemini-2.5-flash"),
                        is_fallback=data.get("is_fallback", False)
                    )
                    session.add(new_entry)
                    session.commit()
            except Exception as e:
                session.rollback()
                logger.warning(f"[m7_ai_insights] Could not cache to database: {e}")
            finally:
                session.close()
    except Exception:
        pass


def _generate_rule_based_fallback(skill_name: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic, transparent explanation when Gemini is unavailable."""
    current_score = metrics.get("current_demand_score", 0)
    growth_rate = metrics.get("growth_rate_percent", 0)
    gap_status = metrics.get("gap_status", "Balanced")
    additional_seats = metrics.get("additional_seats", 0)
    trainers = metrics.get("additional_trainers", 0)
    labs = metrics.get("additional_labs", 0)
    curriculum_status = metrics.get("curriculum_status", "Curriculum alignment verified")
    emerging_raw = metrics.get("emerging_bonus", 0)
    emerging_val = 0
    if isinstance(emerging_raw, (int, float)):
        emerging_val = emerging_raw
    elif isinstance(emerging_raw, str):
        cleaned = emerging_raw.replace("+", "").replace("pts", "").strip()
        try:
            emerging_val = float(cleaned)
        except Exception:
            emerging_val = 0

    district = metrics.get("district", "Maharashtra")
    conf = metrics.get("confidence_12m", 50)

    emerging_text = (
        f"This skill receives an emerging-technology signal boost (+{emerging_val} pts)."
        if emerging_val > 0 else
        "Trend metrics reflect steady industrial baseline requirements."
    )

    narrative = (
        f"**Workforce Signal Analysis for {skill_name} in {district}:**\n\n"
        f"• **Market Demand Trajectory:** {skill_name} holds a current relative demand score of **{current_score}/100** "
        f"backed by a taxonomy annual growth momentum of **{growth_rate:+.1f}%**. {emerging_text}\n"
        f"• **Capacity Status ({gap_status}):** The current training infrastructure exhibits a shortage gap of **{additional_seats} seats**. "
        f"To restore labor market equilibrium over the 12-month horizon, government and vocational centers require approximately **+{trainers} specialized trainer(s)** "
        f"and **+{labs} dedicated lab facility(ies)**.\n"
        f"• **Curriculum Strategy:** {curriculum_status}."
    )

    return {
        "skill": skill_name,
        "district": district,
        "narrative": narrative,
        "recommendations_summary": f"Target +{additional_seats} seats, +{trainers} trainers, and +{labs} practical labs.",
        "model_used": "Deterministic Explainability Engine (Rule-based Fallback)",
        "is_fallback": True,
        "confidence": conf
    }


def generate_skill_insight(skill_name: str, metrics: Dict[str, Any], district: Optional[str] = None) -> Dict[str, Any]:
    """
    Generate an explainable narrative for a specific skill.
    Tries cache first, then official Gemini Flash SDK with backoff, falling back safely.
    """
    target_district = district or metrics.get("district", "Overall Maharashtra")
    gap_status = metrics.get("gap_status", "Shortage")
    cache_key = f"skill:{skill_name}:{target_district}:{gap_status}:{metrics.get('predicted_score_12m', 0)}"

    cached = get_cached_insight(cache_key)
    if cached:
        return cached

    client = _get_gemini_client()
    if client is None:
        fallback = _generate_rule_based_fallback(skill_name, metrics)
        store_cached_insight(cache_key, fallback, insight_type="skill")
        return fallback

    prompt = f"""
You are an expert workforce policy analyst for the Government of Maharashtra and the KaushalSetu platform.
Explain the following PRE-COMPUTED algorithmic demand and skill-gap metrics for '{skill_name}' in {target_district}.

IMPORTANT CONSTRAINTS:
1. Do NOT invent new headcount, salary, or percentage numbers. Use ONLY the exact numbers provided below.
2. The demand score is a transparent 0-100+ composite index (combining posting volume, taxonomy growth, sector growth, employer gap survey, and emerging tech). Explain this clearly.
3. Keep your tone policy-ready, objective, concise, and actionable for ITI principals and government skill directors.
4. Structure the output into two clear sections:
   - "Workforce Demand & Trend Analysis" (2-3 concise paragraphs)
   - "Recommended Government Action Plan" (bullet points for capacity expansion, trainer hiring, and curriculum alignment)

PRE-COMPUTED DATA:
- Skill: {skill_name}
- District / Region: {target_district}
- Current Demand Score (0-100 index): {metrics.get('current_demand_score', 'N/A')}
- Projected 12-Month Score: {metrics.get('predicted_score_12m', 'N/A')} (Confidence: {metrics.get('confidence_12m', 'N/A')}%)
- Skill Growth Rate (Taxonomy): {metrics.get('growth_rate_percent', 'N/A')}%
- Emerging Tech Signal Bonus: {metrics.get('emerging_bonus', 0)} pts
- Obsolescence Risk: {metrics.get('obsolescence_risk', 'Low')}
- Labor Gap Status: {gap_status}
- Additional Training Seats Needed: +{metrics.get('additional_seats', 0)}
- Additional Trainers Needed: +{metrics.get('additional_trainers', 0)} (ratio: ~60 seats/trainer)
- Additional Labs Needed: +{metrics.get('additional_labs', 0)} (ratio: ~300 seats/lab)
- Curriculum Status: {metrics.get('curriculum_status', 'Verify alignment with industry co-occurring skills')}
"""

    # Retry loop with exponential backoff + jitter for HTTP 429
    max_retries = 3
    base_delay = 1.5
    for attempt in range(max_retries):
        try:
            # Using free-tier Flash model family
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            narrative = response.text.strip()
            result = {
                "skill": skill_name,
                "district": target_district,
                "narrative": narrative,
                "recommendations_summary": f"Add +{metrics.get('additional_seats', 0)} seats and +{metrics.get('additional_trainers', 0)} trainers.",
                "model_used": "gemini-2.5-flash (Official Google GenAI SDK)",
                "is_fallback": False,
                "confidence": metrics.get("confidence_12m", 80)
            }
            store_cached_insight(cache_key, result, insight_type="skill")
            return result
        except Exception as e:
            err_str = str(e)
            logger.warning(f"[m7_ai_insights] Attempt {attempt + 1}/{max_retries} failed: {err_str}")
            if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                # Rate limit hit: wait with exponential backoff + random jitter
                sleep_time = (base_delay * (2 ** attempt)) + (random.uniform(0.1, 0.5))
                time.sleep(sleep_time)
                continue
            else:
                # Non-rate-limit error (e.g. invalid key or network issue)
                break

    # Graceful fallback if retries exhausted
    logger.info(f"[m7_ai_insights] Falling back to deterministic narrative for {skill_name}")
    fallback = _generate_rule_based_fallback(skill_name, metrics)
    store_cached_insight(cache_key, fallback, insight_type="skill")
    return fallback


def generate_district_insight(district_name: str, district_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Generate district-level workforce policy narrative."""
    cache_key = f"district:{district_name}:{district_summary.get('total_additional_seats', 0)}"
    cached = get_cached_insight(cache_key)
    if cached:
        return cached

    top_skill = district_summary.get("top_priority_skill", "Technical Skills")
    seats = district_summary.get("total_additional_seats", 0)
    trainers = district_summary.get("total_additional_trainers", 0)
    labs = district_summary.get("total_additional_labs", 0)
    flagged = district_summary.get("skills_flagged", 0)

    narrative = (
        f"**District Workforce Strategy — {district_name}:**\n\n"
        f"• **Priority Overview:** Across {district_name}, the pipeline identifies **{flagged} critical skill domain(s)** requiring capacity expansion, led by high-urgency demand in **{top_skill}**.\n"
        f"• **Infrastructure Roadmap:** Total targeted seat expansion stands at **+{seats:,} seats**, necessitating an allocation of **+{trainers} certified instructors** and **+{labs} practical training laboratory units** to keep pace with industry growth.\n"
        f"• **Policy Recommendation:** Direct district skilling funds toward modernizing local ITI infrastructure and establishing private sector apprenticeship partnerships specifically aligned with {top_skill}."
    )

    result = {
        "district": district_name,
        "narrative": narrative,
        "recommendations_summary": f"Prioritize {top_skill} with +{seats} seats across district ITIs.",
        "model_used": "Deterministic Policy Engine",
        "is_fallback": True
    }
    store_cached_insight(cache_key, result, insight_type="district")
    return result
