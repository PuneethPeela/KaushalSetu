"""
MODULE 2 — Current Demand + Future Prediction  (core AI module)
------------------------------------------------------------------
Honest note on methodology, please read before you present this:

job_postings_maharashtra.csv only covers ~90 days (Jun-Sep 2026). That is
NOT enough history to fit a real time-series model (ARIMA/Prophet/LSTM) —
doing so would just be decoration on top of noise. So instead of pretending
to forecast a trend line we don't have data for, this module builds a
transparent, explainable PREDICTIVE DEMAND SCORE per (skill, district) from
signals that genuinely exist in your data:

    current_demand_score        <- how much a skill is posted for right now
  + skill growth_rate_percent   <- from skills_taxonomy_india (skill-level)
  + district sector growth      <- from industry_demand_sector_growth (district-level)
  + skills_gap_percent          <- employer-reported gap, industry_demand file
  + emerging-tech bonus         <- if the skill appears in emerging_technology_trends
  - obsolescence penalty        <- if skills_taxonomy flags High obsolescence risk

Each horizon (6/12/24 months) compounds the growth signal further out, and
confidence is based on how much underlying posting volume backs the number
(more postings = more confidence, not a magic number).

This is a scoring model, not a black box: every score can be traced back to
the six lines above, which is exactly what Module 2 (Explainability) in the
dashboard shows per skill.
"""

import pandas as pd
import numpy as np
import config
import m1_ingestion
import google_trends          # NEW: live Google Trends bonus signal



def compute_current_demand(long_df: pd.DataFrame) -> pd.DataFrame:
    """Rank skills by current demand, per district and overall."""
    grouped = (
        long_df.groupby(["skill_name", "district"])
        .agg(
            posting_count=("job_id", "count"),
            avg_salary=("salary_offered", "mean"),
            in_taxonomy=("in_taxonomy", "first"),
        )
        .reset_index()
    )

    # 0-100 demand score, scaled within each district so districts with
    # fewer total postings aren't unfairly flattened to near-zero.
    grouped["current_demand_score"] = (
        grouped.groupby("district")["posting_count"]
        .transform(lambda x: 100 * (x - x.min()) / (x.max() - x.min() + 1e-9))
        .round(1)
    )
    return grouped


def _emerging_tech_lookup(emerging_df: pd.DataFrame) -> dict:
    """skill_name -> bonus points if it's named in an emerging-tech
    required_skills list. Severity string -> numeric bonus."""
    severity_bonus = {"Low": 3, "Medium": 8, "High": 15}
    bonus = {}
    for _, row in emerging_df.iterrows():
        skills = [s.strip() for s in str(row["required_skills"]).split(";")]
        pts = severity_bonus.get(row.get("skill_gap_severity"), 5)
        for s in skills:
            bonus[s] = max(bonus.get(s, 0), pts)
    return bonus


def compute_predicted_demand(current_demand: pd.DataFrame, taxonomy: pd.DataFrame,
                              sector_growth: pd.DataFrame, emerging_df: pd.DataFrame,
                              trends_bonus: dict = None) -> pd.DataFrame:  # NEW: trends_bonus added

    df = current_demand.copy()

    # --- skill-level signal: growth_rate_percent & obsolescence, from taxonomy ---
    tax_signal = (
        taxonomy.groupby("skill_name")
        .agg(growth_rate_percent=("growth_rate_percent", "mean"),
             obsolescence_risk=("obsolescence_risk", "first"),
             demand_trend=("demand_trend", "first"))
        .reset_index()
    )
    df = df.merge(tax_signal, on="skill_name", how="left")

    # --- district-level signal: average sector growth & skills gap in that district ---
    district_signal = (
        sector_growth.groupby("district")
        .agg(district_growth_rate=("growth_rate_percent", "mean"),
             district_skills_gap=("skills_gap_percent", "mean"))
        .reset_index()
    )
    df = df.merge(district_signal, on="district", how="left")

    # --- emerging tech bonus (static CSV) + live Google Trends bonus [NEW] ---
    bonus_lookup = _emerging_tech_lookup(emerging_df)
    df["static_emerging_bonus"] = df["skill_name"].map(bonus_lookup).fillna(0)          # from CSV
    df["trends_bonus"]          = df["skill_name"].map(trends_bonus or {}).fillna(0)    # from Google Trends [NEW]
    # Take the higher of the two signals: if either source says "high trend", honour it
    df["emerging_bonus"] = df[["static_emerging_bonus", "trends_bonus"]].max(axis=1)   # [NEW]


    # fill signal gaps with neutral values (0 growth, no known obsolescence)
    df["growth_rate_percent"] = df["growth_rate_percent"].fillna(0)
    df["district_growth_rate"] = df["district_growth_rate"].fillna(0)
    df["district_skills_gap"] = df["district_skills_gap"].fillna(0)

    obsolescence_penalty = {"High": -15, "Medium": -5, "Low": 0}
    df["obsolescence_penalty"] = df["obsolescence_risk"].map(obsolescence_penalty).fillna(0)

    # --- combine into one predicted score per horizon ---
    # weights are intentionally simple/transparent — tune once you have
    # ground truth to validate against (e.g. district_training_plans.csv)
    for h in config.HORIZONS:
        years = h / 12
        compounded_growth = (df["growth_rate_percent"] + df["district_growth_rate"]) / 2 * years
        score = (
            df["current_demand_score"]
            + compounded_growth
            + df["district_skills_gap"] * 0.3
            + df["emerging_bonus"]
            + df["obsolescence_penalty"]
        )
        df[f"predicted_score_{h}m"] = score.clip(lower=0, upper=130).round(1)

        # confidence: more postings backing the number = more confidence,
        # penalized when we had to fill in missing signals
        base_conf = 50 + np.minimum(df["posting_count"] * 2, 35)
        penalty = np.where(df["growth_rate_percent"] == 0, 8, 0)
        df[f"confidence_{h}m"] = (base_conf - penalty).clip(lower=40, upper=95).round(0)

    def _band(score):
        if score >= 90: return "Very High"
        if score >= 65: return "High"
        if score >= 35: return "Medium"
        return "Low"

    for h in config.HORIZONS:
        df[f"demand_band_{h}m"] = df[f"predicted_score_{h}m"].apply(_band)

    return df


def run():
    long_df, taxonomy = m1_ingestion.run()
    sector_growth = pd.read_csv(config.FILE_SECTOR_GROWTH)
    emerging_df = pd.read_csv(config.FILE_EMERGING_TECH)

    # --- NEW: live Google Trends bonus ---
    # Fetch trend interest for every unique skill in the job postings.
    # Skipped if config.TRENDS_ENABLED = False (useful for offline / faster runs).
    trends_bonus = {}
    if getattr(config, "TRENDS_ENABLED", True):
        skills_list = long_df["skill_name"].dropna().unique().tolist()
        trends_bonus = google_trends.fetch_google_trends(
            skills_list,
            geo=getattr(config, "TRENDS_GEO", "IN-MH"),
            timeframe=getattr(config, "TRENDS_TIMEFRAME", "today 3-m"),
        )
    else:
        print("[M2] Google Trends skipped (TRENDS_ENABLED = False in config.py)")

    current = compute_current_demand(long_df)
    predicted = compute_predicted_demand(current, taxonomy, sector_growth, emerging_df, trends_bonus)  # NEW: pass trends_bonus

    current.to_csv(config.OUT_CURRENT_DEMAND, index=False)
    predicted.to_csv(config.OUT_PREDICTED_DEMAND, index=False)
    print(f"[M2] wrote {config.OUT_CURRENT_DEMAND} ({len(current)} rows)")
    print(f"[M2] wrote {config.OUT_PREDICTED_DEMAND} ({len(predicted)} rows)")

    top = predicted.sort_values("predicted_score_12m", ascending=False).head(5)
    print("\n[M2] Top 5 predicted (12mo) skill x district:")
    print(top[["skill_name", "district", "current_demand_score", "predicted_score_12m",
               "demand_band_12m", "confidence_12m"]].to_string(index=False))

    return predicted


if __name__ == "__main__":
    run()

