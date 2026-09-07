"""
MODULE 6 — Curriculum Alignment
------------------------------------------------------------------
Question this answers: "Does this course actually teach what employers
are hiring for?"

Method (only works for the 16 courses that have a course_skills_mapping
entry — the other 66 course names in training_centers have no curriculum
detail, so they're skipped, not guessed at):

  1. Take the skills a course teaches (course_skills_mapping.skill_name).
  2. Find every job posting that asks for AT LEAST ONE of those skills —
     these are the postings this course is actually relevant to.
  3. Look at what ELSE those same postings commonly ask for. That's the
     real-world "skill bundle" employers expect alongside this course's
     content.
  4. Alignment % = how much of that bundle the course actually teaches.
     Missing skills = the frequently co-required skills it doesn't teach.

This is explainable and grounded in real postings, not a guess at what a
course "should" contain.
"""

import pandas as pd
import config
import m1_ingestion

MIN_COOCCURRING_SKILLS = 8   # how many top co-occurring skills define "the bundle"


def compute_alignment(long_df: pd.DataFrame, course_skills: pd.DataFrame) -> pd.DataFrame:
    course_to_taught = (
        course_skills.groupby("course_name")["skill_name"]
        .apply(lambda s: set(s))
        .to_dict()
    )

    rows = []
    for course, taught_skills in course_to_taught.items():
        # jobs relevant to this course: postings requiring >=1 taught skill
        relevant_job_ids = long_df.loc[long_df["skill_name"].isin(taught_skills), "job_id"].unique()
        relevant_postings = long_df[long_df["job_id"].isin(relevant_job_ids)]

        if len(relevant_postings) == 0:
            rows.append({
                "course_name": course, "taught_skills": sorted(taught_skills),
                "alignment_percent": None, "missing_skills": [], "matched_postings": 0,
                "note": "No matching job postings found for this course's skills"
            })
            continue

        bundle = (
            relevant_postings["skill_name"].value_counts()
            .head(MIN_COOCCURRING_SKILLS)
            .index.tolist()
        )
        matched = [s for s in bundle if s in taught_skills]
        missing = [s for s in bundle if s not in taught_skills]
        alignment_pct = round(100 * len(matched) / len(bundle), 1) if bundle else None

        rows.append({
            "course_name": course,
            "taught_skills": sorted(taught_skills),
            "in_demand_bundle": bundle,
            "alignment_percent": alignment_pct,
            "missing_skills": missing,
            "matched_postings": len(relevant_job_ids),
            "note": "",
        })

    return pd.DataFrame(rows).sort_values("alignment_percent", ascending=True, na_position="last")


def run():
    long_df, _ = m1_ingestion.run()
    course_skills = pd.read_csv(config.FILE_COURSE_SKILLS)
    alignment = compute_alignment(long_df, course_skills)

    out_path = config.OUT_CURRICULUM_ALIGNMENT
    # lists -> semicolon strings for a clean CSV
    export = alignment.copy()
    for col in ["taught_skills", "in_demand_bundle", "missing_skills"]:
        if col in export.columns:
            export[col] = export[col].apply(lambda v: "; ".join(v) if isinstance(v, list) else v)
    export.to_csv(out_path, index=False)
    print(f"[M6] wrote {out_path} ({len(export)} courses)")

    print("\n[M6] Lowest-alignment courses (most in need of curriculum update):")
    print(export[["course_name", "alignment_percent", "missing_skills", "matched_postings"]].head(6).to_string(index=False))
    return alignment


if __name__ == "__main__":
    run()
