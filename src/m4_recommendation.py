"""
MODULE 4 — Training Recommendation Engine  (main deliverable)
------------------------------------------------------------------
Turns every Critical Shortage / Shortage row from Module 3 into a concrete,
government-actionable recommendation: additional seats, trainers, labs, and
which curriculum modules are missing.

Trainer/lab ratios (SEATS_PER_TRAINER, SEATS_PER_LAB in config.py) are a
placeholder assumption — replace them with real ratios from your training
centre data if you have them (e.g. derive from existing
total_capacity / total_trainers averages instead of a flat constant).

At the end, this module rolls results up to district level and prints a
side-by-side comparison against district_training_plans.csv's own
`critical_skills_gaps` field — not because that file is ground truth to
copy, but as a sanity check: if our independently-computed gaps look wildly
different from the existing plan, that's worth investigating before you
present this, not after.
"""

import pandas as pd
import config
import m3_supply_gap


def build_recommendations(gap_df: pd.DataFrame, course_skills: pd.DataFrame) -> pd.DataFrame:
    needs_action = gap_df[gap_df["gap_status"].str.contains("Shortage", na=False)].copy()
    needs_action = needs_action[needs_action["gap_units"] > 0]

    needs_action["additional_seats"] = needs_action["gap_units"].round(0)
    needs_action["additional_trainers"] = (needs_action["additional_seats"] / config.SEATS_PER_TRAINER).apply(
        lambda x: max(1, round(x))
    )
    needs_action["additional_labs"] = (needs_action["additional_seats"] / config.SEATS_PER_LAB).apply(
        lambda x: max(1, round(x)) if x > 0 else 0
    )
    needs_action["priority"] = needs_action["gap_status"].map({
        "Critical Shortage": "High",
        "Critical Shortage (no training supply at all)": "High",
        "Shortage": "Medium",
    }).fillna("Medium")

    # which skills already have SOME curriculum coverage vs need a brand new module
    mapped_skills = set(course_skills["skill_name"].unique())
    needs_action["curriculum_status"] = needs_action["skill_name"].apply(
        lambda s: "Add to existing course" if s in mapped_skills else "No course teaches this yet — new module needed"
    )

    cols = ["skill_name", "district", "gap_status", "priority", "estimated_demand_headcount",
            "available_seats", "additional_seats", "additional_trainers", "additional_labs",
            "curriculum_status", "confidence_12m", "demand_band_12m"]
    return needs_action[cols].sort_values(["priority", "additional_seats"], ascending=[True, False])


def build_district_summary(recommendations: pd.DataFrame) -> pd.DataFrame:
    summary = (
        recommendations.groupby("district")
        .agg(
            skills_flagged=("skill_name", "count"),
            total_additional_seats=("additional_seats", "sum"),
            total_additional_trainers=("additional_trainers", "sum"),
            total_additional_labs=("additional_labs", "sum"),
            high_priority_skills=("priority", lambda s: (s == "High").sum()),
        )
        .reset_index()
        .sort_values("total_additional_seats", ascending=False)
    )
    top_skill_per_district = (
        recommendations.sort_values("additional_seats", ascending=False)
        .groupby("district")
        .first()["skill_name"]
        .rename("top_priority_skill")
    )
    return summary.merge(top_skill_per_district, on="district", how="left")


def compare_with_existing_plans(district_summary: pd.DataFrame):
    plans = pd.read_csv(config.FILE_DISTRICT_PLANS)
    merged = district_summary.merge(
        plans[["district", "critical_skills_gaps", "recommended_capacity_expansion"]],
        on="district", how="left"
    )
    print("\n[M4] Sanity check vs district_training_plans.csv (existing plan):")
    print(merged[["district", "top_priority_skill", "critical_skills_gaps",
                   "total_additional_seats", "recommended_capacity_expansion"]].head(8).to_string(index=False))


def run():
    gap_df = m3_supply_gap.run()
    course_skills = pd.read_csv(config.FILE_COURSE_SKILLS)

    recommendations = build_recommendations(gap_df, course_skills)
    district_summary = build_district_summary(recommendations)

    recommendations.to_csv(config.OUT_RECOMMENDATIONS, index=False)
    district_summary.to_csv(config.OUT_DISTRICT_SUMMARY, index=False)
    print(f"\n[M4] wrote {config.OUT_RECOMMENDATIONS} ({len(recommendations)} rows)")
    print(f"[M4] wrote {config.OUT_DISTRICT_SUMMARY} ({len(district_summary)} rows)")

    compare_with_existing_plans(district_summary)
    return recommendations, district_summary


if __name__ == "__main__":
    run()
