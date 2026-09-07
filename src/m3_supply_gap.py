"""
MODULE 3 — Skill Supply & Gap Detection
------------------------------------------
Supply side: training_centers_maharashtra.csv gives capacity/enrollment per
COURSE, not per SKILL. course_skills_mapping.csv is the bridge between the
two — but it only covers 16 of the 82 course names that actually appear in
training_centers. For the other courses we genuinely don't know which
skills they teach, so this module marks those skill/district combinations
`supply_data_available = False` rather than guessing a number. Don't let a
dashboard silently show "0 supply" for those — that's a data gap, not a
finding.

Demand side: predicted_score from Module 2 is a relative 0-130 score, not a
headcount. To compare against supply (which IS a headcount — seats), we
convert the score into an estimated number of people using the actual
posting volume for that skill/district, scaled by the predicted growth
multiplier. This is an approximation — document it as such in your report;
it is a reasonable proxy, not a measured quantity.
"""

import pandas as pd
import config
import m2_demand_prediction


def compute_skill_supply() -> pd.DataFrame:
    centers = pd.read_csv(config.FILE_TRAINING_CENTERS)
    course_skills = pd.read_csv(config.FILE_COURSE_SKILLS)

    course_to_skills = (
        course_skills.groupby("course_name")["skill_name"]
        .apply(lambda s: sorted(set(s)))
        .to_dict()
    )

    centers["available_seats"] = (centers["total_capacity"] - centers["current_enrollment"]).clip(lower=0)

    rows = []
    for _, c in centers.iterrows():
        skills_for_course = course_to_skills.get(c["course_name"])
        if not skills_for_course:
            # No mapping exists for this course — record it as unmapped,
            # not zero.
            rows.append({
                "district": c["district"], "course_name": c["course_name"],
                "skill_name": None, "total_capacity": c["total_capacity"],
                "available_seats": c["available_seats"],
                "total_trainers": c["total_trainers"],
                "placement_rate_percent": c["placement_rate_percent"],
                "supply_data_available": False,
            })
            continue
        for skill in skills_for_course:
            rows.append({
                "district": c["district"], "course_name": c["course_name"],
                "skill_name": skill, "total_capacity": c["total_capacity"],
                "available_seats": c["available_seats"],
                "total_trainers": c["total_trainers"],
                "placement_rate_percent": c["placement_rate_percent"],
                "supply_data_available": True,
            })
    supply_long = pd.DataFrame(rows)

    supply_by_skill_district = (
        supply_long[supply_long["supply_data_available"]]
        .groupby(["skill_name", "district"])
        .agg(
            total_capacity=("total_capacity", "sum"),
            available_seats=("available_seats", "sum"),
            total_trainers=("total_trainers", "sum"),
            avg_placement_rate=("placement_rate_percent", "mean"),
            course_count=("course_name", "nunique"),
        )
        .reset_index()
    )
    return supply_by_skill_district


def _classify_gap(ratio: float) -> str:
    if pd.isna(ratio):
        return "No supply data"
    if ratio >= config.GAP_CRITICAL_RATIO:
        return "Critical Shortage"
    if ratio >= config.GAP_SHORTAGE_RATIO:
        return "Shortage"
    if ratio <= config.GAP_OVERSUPPLY_RATIO:
        return "Oversupply"
    return "Balanced"


def compute_gap(predicted_demand: pd.DataFrame, supply: pd.DataFrame) -> pd.DataFrame:
    df = predicted_demand.merge(supply, on=["skill_name", "district"], how="left")

    # Convert the 12-month predicted score into an estimated headcount need:
    # posting_count is the real observed volume; the score's ratio to
    # current_demand_score tells us the estimated growth multiplier.
    growth_multiplier = (df["predicted_score_12m"] / df["current_demand_score"].replace(0, 1)).clip(lower=1)
    df["estimated_demand_headcount"] = (df["posting_count"] * growth_multiplier * 4).round(0)
    # x4 rough annualization: postings observed in a ~90-day window -> yearly

    df["available_seats"] = df["available_seats"].fillna(0)
    df["gap_ratio"] = df["estimated_demand_headcount"] / df["available_seats"].replace(0, pd.NA)
    df["gap_units"] = (df["estimated_demand_headcount"] - df["available_seats"]).round(0)
    df["gap_status"] = df["gap_ratio"].apply(_classify_gap)
    # if there was never any supply data for this course/skill, say so explicitly
    df.loc[df["available_seats"] == 0, "gap_status"] = df.loc[df["available_seats"] == 0, "gap_status"].replace(
        "Critical Shortage", "Critical Shortage (no training supply at all)"
    )
    return df


def run():
    predicted = m2_demand_prediction.run()
    supply = compute_skill_supply()
    gap = compute_gap(predicted, supply)

    supply.to_csv(config.OUT_SUPPLY, index=False)
    gap.to_csv(config.OUT_GAP, index=False)
    print(f"[M3] wrote {config.OUT_SUPPLY} ({len(supply)} rows)")
    print(f"[M3] wrote {config.OUT_GAP} ({len(gap)} rows)")

    critical = gap[gap["gap_status"].str.contains("Critical", na=False)].sort_values(
        "gap_units", ascending=False
    )
    print(f"\n[M3] {len(critical)} (skill, district) rows flagged critical shortage. Top 5:")
    print(critical[["skill_name", "district", "estimated_demand_headcount", "available_seats",
                     "gap_units", "gap_status"]].head(5).to_string(index=False))
    return gap


if __name__ == "__main__":
    run()
