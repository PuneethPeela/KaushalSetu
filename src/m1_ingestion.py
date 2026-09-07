"""
MODULE 1 — Data Ingestion & Skill Extraction
---------------------------------------------
What this actually does with YOUR data (read this before assuming it's generic NLP):

`skills_required` in job_postings_maharashtra.csv is already a clean
semicolon-separated list (e.g. "Python; TensorFlow; PyTorch"), not free-text
job-description paragraphs. So this module does NOT run spaCy/NER — that
would be solving a problem you don't have. Instead it does the real work
that a clean-looking dataset still needs:

  1. Load + de-duplicate every raw file.
  2. Split `skills_required` into one row per (job, skill) — this is the
     "explode" step that turns wide job postings into a long skill table.
  3. Normalize skill text (trim, casing, whitespace) so "python", "Python "
     and "PYTHON" collapse into one skill.
  4. Match each normalized skill against the official skills_taxonomy list.
     Skills that don't match (e.g. "NumPy", "Scikit-learn", "Git" — real
     examples from your data that aren't in the taxonomy) are kept but
     flagged `in_taxonomy = False` so later modules don't silently drop them.

Run standalone for a quick check: `python src/m1_ingestion.py`
"""

import pandas as pd
import re
import config


def _norm_skill(name: str) -> str:
    """Trim whitespace and collapse casing differences without destroying
    intentional capitalization for acronyms (SQL, NLP, AWS, etc.)."""
    if pd.isna(name):
        return name
    cleaned = re.sub(r"\s+", " ", str(name).strip())
    return cleaned


def load_job_postings() -> pd.DataFrame:
    df = pd.read_csv(config.FILE_JOB_POSTINGS)
    before = len(df)
    df = df.drop_duplicates(subset=["job_id"])
    df["posted_date"] = pd.to_datetime(df["posted_date"], errors="coerce")
    df["location"] = df["location"].str.strip()
    df["industry"] = df["industry"].str.strip()
    dropped = before - len(df)
    if dropped:
        print(f"[M1] job_postings: dropped {dropped} duplicate job_id rows")
    return df


def load_skills_taxonomy() -> pd.DataFrame:
    df = pd.read_csv(config.FILE_SKILLS_TAXONOMY)
    df["skill_name"] = df["skill_name"].apply(_norm_skill)
    return df


def explode_job_skills(job_postings: pd.DataFrame, taxonomy: pd.DataFrame) -> pd.DataFrame:
    """Turn one row per job posting into one row per (job, skill).
    This is the 'skill extraction' step — parsing, not NLP, because the
    source column is already structured."""
    taxonomy_skills = set(taxonomy["skill_name"].unique())

    rows = []
    for _, job in job_postings.iterrows():
        if pd.isna(job["skills_required"]):
            continue
        for raw_skill in str(job["skills_required"]).split(";"):
            skill = _norm_skill(raw_skill)
            if not skill:
                continue
            rows.append({
                "job_id": job["job_id"],
                "skill_name": skill,
                "in_taxonomy": skill in taxonomy_skills,
                "district": job["location"],
                "industry": job["industry"],
                "job_title": job["job_title"],
                "experience_required": job["experience_required"],
                "salary_offered": job["salary_offered"],
                "posted_date": job["posted_date"],
                "job_type": job["job_type"],
            })
    long_df = pd.DataFrame(rows)
    unmatched = long_df.loc[~long_df["in_taxonomy"], "skill_name"].nunique()
    print(f"[M1] exploded {len(job_postings)} postings into {len(long_df)} (job, skill) rows")
    print(f"[M1] {long_df['skill_name'].nunique()} distinct skills found; "
          f"{unmatched} not present in skills_taxonomy_india.csv (kept, flagged)")
    return long_df


def run():
    postings = load_job_postings()
    taxonomy = load_skills_taxonomy()
    long_df = explode_job_skills(postings, taxonomy)

    long_df.to_csv(config.OUT_SKILL_DEMAND_LONG, index=False)
    taxonomy.to_csv(config.OUT_SKILLS_TAXONOMY_CLEAN, index=False)
    print(f"[M1] wrote {config.OUT_SKILL_DEMAND_LONG}")
    print(f"[M1] wrote {config.OUT_SKILLS_TAXONOMY_CLEAN}")
    return long_df, taxonomy


if __name__ == "__main__":
    run()
