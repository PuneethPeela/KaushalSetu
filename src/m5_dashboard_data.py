"""
MODULE 5 — Dashboard Data Aggregation
----------------------------------------
Not a modelling step — this just reshapes M1-M4's output CSVs into the
compact JSON structure the dashboard's JavaScript expects (top skills,
per-skill forecast series, gap list, one headline recommendation, district
rollup). Kept separate from M1-M4 so the modelling code stays modelling
code and the "make it presentable" code stays here.

Includes EVERY skill found in the postings data (all had well over the
MIN_POSTINGS_FOR_FORECAST threshold in testing), not just a hand-picked
top few — so the dashboard's skill picker covers the full list: Java,
TensorFlow, PyTorch, Deep Learning, NLP, Scikit-learn, and everything else
actually present in job_postings_maharashtra.csv. Note: literal tags
"AI/ML" and "C++" do not appear anywhere in the source data — if your real
data uses those exact labels, they'll show up automatically once ingested;
right now the closest present equivalents are the individual ML/AI
libraries and Java (no C++ at all in this dataset).

Also builds a "3-year modeled trajectory" per skill for historical growth
context — see the big warning in `build_modeled_trajectory()` below before
presenting this as real history, because it isn't.

Run standalone to just regenerate outputs/dashboard_data.json from
whatever is currently in outputs/ (without re-running the whole pipeline):
    python src/m5_dashboard_data.py
"""

import json
import pandas as pd
import config

MIN_POSTINGS_FOR_FORECAST = 5  # skip only genuinely too-sparse skills


def build_modeled_trajectory(current_value: float, growth_rate_percent: float, years_back: int = 3):
    """
    IMPORTANT — read before using this anywhere near a judge or a report:

    None of the 8 source datasets contain a real multi-year (3-4 year)
    history of job-posting demand. job_postings_maharashtra.csv covers
    ~90 days. skills_taxonomy_india.csv gives ONE current growth_rate_percent
    figure per skill, not a time series.

    This function does NOT recover real history. It backward-compounds
    today's demand score using that single stated growth rate, i.e. it
    assumes the growth rate has been constant for the last `years_back`
    years and works backward from today. That's a reasonable illustrative
    story ("if this growth rate has held, here's roughly what the trend
    looks like") but it is a MODEL, not a MEASUREMENT. Label it as such
    every time it's shown.
    """
    points = [current_value]
    for _ in range(years_back):
        points.insert(0, round(points[0] / (1 + growth_rate_percent / 100), 1))
    return points


def build() -> dict:
    long_df = pd.read_csv(config.OUT_SKILL_DEMAND_LONG)
    long_df["posted_date"] = pd.to_datetime(long_df["posted_date"])
    pred = pd.read_csv(config.OUT_PREDICTED_DEMAND)
    gap = pd.read_csv(config.OUT_GAP)
    rec = pd.read_csv(config.OUT_RECOMMENDATIONS)
    dist = pd.read_csv(config.OUT_DISTRICT_SUMMARY)

    posting_counts = long_df.groupby("skill_name").size()
    all_skills = sorted(posting_counts[posting_counts >= MIN_POSTINGS_FOR_FORECAST].index.tolist())
    in_taxonomy_lookup = long_df.groupby("skill_name")["in_taxonomy"].any().to_dict()

    # ---------- national rank list (top 10, for the Overview screen only) ----------
    nat_counts = long_df.groupby("skill_name").size().rename("posting_count").reset_index()
    nat_max, nat_min = nat_counts["posting_count"].max(), nat_counts["posting_count"].min()
    nat_counts["demand_score"] = (100 * (nat_counts["posting_count"] - nat_min) / (nat_max - nat_min + 1e-9)).round(1)
    growth_lookup = pred.groupby("skill_name")["growth_rate_percent"].mean().round(1).to_dict()
    nat_counts["growth"] = nat_counts["skill_name"].map(growth_lookup).fillna(0)
    rank_list = nat_counts.sort_values("posting_count", ascending=False).head(10)
    rank_list_json = [
        {"name": r.skill_name, "demand": r.demand_score,
         "trend": "up" if r.growth >= 0 else "down",
         "trendVal": f"{'+' if r.growth >= 0 else ''}{r.growth}%"}
        for r in rank_list.itertuples()
    ]

    # ---------- forecast series: real weekly history + predicted horizons + modeled 3yr context ----------
    max_date = long_df["posted_date"].max()
    min_date = long_df["posted_date"].min()
    trim_days = (max_date - min_date).days % 7
    cutoff = max_date - pd.Timedelta(days=trim_days)
    weekly_df = long_df[long_df["posted_date"] <= cutoff].copy()
    weekly_df["week"] = weekly_df["posted_date"].dt.to_period("W").apply(lambda p: p.start_time.strftime("%d %b"))

    forecast_skills = []
    for skill in all_skills:
        sub = weekly_df[weekly_df["skill_name"] == skill]
        weekly = sub.groupby("week").size()
        weekly = weekly.reindex(sorted(weekly.index, key=lambda w: pd.to_datetime(w + " 2026")))
        hist_counts = weekly.tolist()
        hist_weeks = weekly.index.tolist()
        if not hist_counts:
            continue

        sp = pred[pred["skill_name"] == skill]
        avg_current = round(sp["current_demand_score"].mean(), 1) if len(sp) else 0
        avg_p6 = round(sp["predicted_score_6m"].mean(), 1) if len(sp) else 0
        avg_p12 = round(sp["predicted_score_12m"].mean(), 1) if len(sp) else 0
        avg_p24 = round(sp["predicted_score_24m"].mean(), 1) if len(sp) else 0
        avg_conf = int(round(sp["confidence_12m"].mean())) if len(sp) else 50
        growth = round(sp["growth_rate_percent"].mean(), 1) if len(sp) else 0
        dist_growth = round(sp["district_growth_rate"].mean(), 1) if len(sp) else 0
        skills_gap = round(sp["district_skills_gap"].mean(), 1) if len(sp) else 0
        emerging = round(sp["emerging_bonus"].mean(), 1) if len(sp) else 0
        obsolescence = (sp["obsolescence_risk"].mode()[0]
                         if len(sp) and sp["obsolescence_risk"].notna().any() else "Not in taxonomy")
        is_in_taxonomy = bool(in_taxonomy_lookup.get(skill, False))

        scale = (avg_current / hist_counts[-1]) if hist_counts and hist_counts[-1] > 0 else 1
        hist_scaled = [round(v * scale, 1) for v in hist_counts]

        trajectory = build_modeled_trajectory(avg_current, growth, years_back=3)

        forecast_skills.append({
            "name": skill, "periods": hist_weeks, "hist": hist_scaled,
            "fut6": avg_p6, "fut12": avg_p12, "fut24": avg_p24,
            "current": avg_current, "confidence": avg_conf,
            "in_taxonomy": is_in_taxonomy,
            "trajectory_3yr": trajectory,  # [3yr ago, 2yr ago, 1yr ago, today] — MODELED, see build_modeled_trajectory
            "why": [
                ["Skill growth rate (taxonomy)", f"{'+' if growth >= 0 else ''}{growth}%", "pos" if growth >= 0 else "neg"],
                ["District sector growth (avg)", f"{'+' if dist_growth >= 0 else ''}{dist_growth}%", "pos" if dist_growth >= 0 else "neg"],
                ["Employer-reported skills gap", f"{skills_gap}%", "pos" if skills_gap > 20 else "neg"],
                ["Emerging-tech signal bonus", f"+{emerging} pts" if emerging > 0 else "None", "pos" if emerging > 0 else "neg"],
                ["Obsolescence risk", obsolescence, "neg" if obsolescence == "High" else "pos"],
                ["Postings backing this score (90 days)", f"{sum(hist_counts)}", "pos"],
            ]
        })

    # ---------- gap list ----------
    gap_top = gap[gap["gap_status"].str.contains("Shortage", na=False)].sort_values("gap_units", ascending=False).head(8)
    gap_json = [
        {"name": r.skill_name, "district": r.district, "demand": int(r.estimated_demand_headcount),
         "supply": int(r.available_seats), "status": "critical" if "Critical" in r.gap_status else "shortage"}
        for r in gap_top.itertuples()
    ]

    # ---------- headline recommendation ----------
    rec_sorted = rec.sort_values("additional_seats", ascending=False)
    top_rec = rec_sorted.iloc[0]
    rec_json = {
        "skill": top_rec["skill_name"], "district": top_rec["district"],
        "seats": int(top_rec["additional_seats"]), "trainers": int(top_rec["additional_trainers"]),
        "labs": int(top_rec["additional_labs"]), "confidence": int(top_rec["confidence_12m"]),
        "curriculum_status": top_rec["curriculum_status"], "gap_status": top_rec["gap_status"],
        "priority": top_rec["priority"], "demand_band": top_rec["demand_band_12m"],
    }
    other_recs_json = [
        {"skill": r["skill_name"], "district": r["district"], "seats": int(r["additional_seats"]),
         "trainers": int(r["additional_trainers"]), "labs": int(r["additional_labs"]),
         "confidence": int(r["confidence_12m"]), "priority": r["priority"],
         "gap_status": r["gap_status"], "curriculum_status": r["curriculum_status"]}
        for _, r in rec_sorted[rec_sorted["skill_name"] != top_rec["skill_name"]]
                      .drop_duplicates("skill_name").head(6).iterrows()
    ]

    # ---------- districts ----------
    districts_json = []
    for _, d in dist.sort_values("total_additional_seats", ascending=False).iterrows():
        d_recs = rec[rec["district"] == d["district"]].sort_values("additional_seats", ascending=False).head(4)
        priorities = [[r["skill_name"], r["demand_band_12m"]] for _, r in d_recs.iterrows()]
        status = "critical" if d["high_priority_skills"] > 0 else "shortage"
        districts_json.append({
            "name": d["district"], "topSkill": d["top_priority_skill"],
            "gapSeats": int(d["total_additional_seats"]), "trainers": int(d["total_additional_trainers"]),
            "labs": int(d["total_additional_labs"]), "status": status, "priorities": priorities,
        })

    # ---------- oversupply example ----------
    over = gap[gap["gap_status"] == "Oversupply"].sort_values("gap_units")
    oversupply_json = None
    if len(over):
        o = over.iloc[0]
        oversupply_json = {"skill": o["skill_name"], "district": o["district"],
                            "demand": int(o["estimated_demand_headcount"]), "supply": int(o["available_seats"])}

    # ---------- curriculum alignment (M6) ----------
    curriculum_json = []
    try:
        align = pd.read_csv(config.OUT_CURRICULUM_ALIGNMENT)
        align = align[align["alignment_percent"].notna()].sort_values("alignment_percent")
        for _, r in align.head(10).iterrows():
            curriculum_json.append({
                "course": r["course_name"],
                "alignment": round(float(r["alignment_percent"]), 1),
                "missing": [s.strip() for s in str(r["missing_skills"]).split(";") if s.strip()],
                "matched_postings": int(r["matched_postings"]),
            })
    except FileNotFoundError:
        pass  # M6 hasn't been run yet — dashboard will show "no data" for this tab

    # ---------- taxonomy-wide growth overview ----------
    # Uses skills_taxonomy_india.csv directly (not job postings), so it includes
    # skills like C++ and Machine Learning that have a taxonomy growth rate but
    # zero postings in the current 90-day job_postings sample. This is the
    # closest honest substitute for "3-4 years of trend" — the taxonomy vendor's
    # own growth judgment, not a time series we measured ourselves.
    tax = pd.read_csv(config.OUT_SKILLS_TAXONOMY_CLEAN)
    tax_agg = (
        tax.groupby("skill_name")
        .agg(growth_rate_percent=("growth_rate_percent", "mean"),
             demand_trend=("demand_trend", "first"),
             obsolescence_risk=("obsolescence_risk", "first"))
        .reset_index()
    )
    tax_agg["postings_count"] = tax_agg["skill_name"].map(posting_counts).fillna(0).astype(int)
    tax_agg = tax_agg.sort_values("growth_rate_percent", ascending=False)
    top_growth = tax_agg.head(12)
    top_decline = tax_agg.sort_values("growth_rate_percent").head(5)
    ALWAYS_INCLUDE = ["Java", "C++", "Machine Learning", "Python", "JavaScript"]
    always_rows = tax_agg[tax_agg["skill_name"].isin(ALWAYS_INCLUDE)]
    growth_overview_json = [
        {"skill": r["skill_name"], "growth": round(float(r["growth_rate_percent"]), 1),
         "trend": r["demand_trend"], "obsolescence": r["obsolescence_risk"],
         "postings": int(r["postings_count"]), "has_real_postings": bool(r["postings_count"] > 0)}
        for _, r in pd.concat([top_growth, top_decline, always_rows]).drop_duplicates("skill_name")
                      .sort_values("growth_rate_percent", ascending=False).iterrows()
    ]

    return {
        "rank_list": rank_list_json,
        "forecast_skills": forecast_skills,
        "gap_list": gap_json,
        "recommendation": rec_json,
        "other_recommendations": other_recs_json,
        "districts": districts_json,
        "oversupply_example": oversupply_json,
        "curriculum_alignment": curriculum_json,
        "growth_overview": growth_overview_json,
        "stats": {
            "postings": int(long_df["job_id"].nunique()),
            "skills": int(long_df["skill_name"].nunique()),
            "districts": int(dist["district"].nunique()),
            "critical": int(gap["gap_status"].str.contains("Critical", na=False).sum()),
        }
    }


def run():
    data = build()
    out_path = config.OUT_DASHBOARD_DATA
    with open(out_path, "w") as f:
        json.dump(data, f, indent=2)
    print(f"[M5] wrote {out_path} — {len(data['forecast_skills'])} skills included (all, not just top picks)")
    return data


if __name__ == "__main__":
    run()
