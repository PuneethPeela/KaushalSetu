"""
init_db.py
----------
Initializes database tables on Neon Postgres (or any configured DATABASE_URL)
using SQLAlchemy create_all. Also imports initial data from existing CSVs
in outputs/ if the tables are empty.
"""

import os
import sys
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from db import get_engine, SessionLocal, Base, is_db_available
import config
from models import (
    JobPostingSkill, SkillTaxonomy, CurrentDemand, PredictedDemand,
    SkillSupply, SkillGap, TrainingRecommendation, DistrictSummary,
    CurriculumAlignment, AIInsightCache, PipelineRun
)


def init_database():
    engine = get_engine()
    if engine is None:
        print("[init_db] No DATABASE_URL configured or engine could not be initialized.")
        print("[init_db] Skipping database initialization. Local CSV outputs will be used.")
        return False

    print("[init_db] Creating all tables on configured database...")
    Base.metadata.create_all(bind=engine)
    print("[init_db] Tables successfully verified / created.")

    # Seed data from outputs/ if empty
    session = SessionLocal()
    try:
        rec_count = session.query(TrainingRecommendation).count()
        if rec_count == 0 and os.path.exists(config.OUT_RECOMMENDATIONS):
            print("[init_db] Database is empty. Seeding initial data from existing outputs/*.csv ...")
            sync_csv_to_db(session)
            print("[init_db] Seeding completed.")
        else:
            print(f"[init_db] Database already contains records ({rec_count} recommendations).")
    except Exception as e:
        print(f"[init_db] Error checking or seeding database: {e}")
    finally:
        session.close()

    return True


def sync_csv_to_db(session=None):
    """Populate database tables from the generated CSV files."""
    engine = get_engine()
    if engine is None:
        return

    should_close = False
    if session is None:
        session = SessionLocal()
        should_close = True

    try:
        # 1. Taxonomy
        if os.path.exists(config.OUT_SKILLS_TAXONOMY_CLEAN):
            df = pd.read_csv(config.OUT_SKILLS_TAXONOMY_CLEAN).drop_duplicates("skill_name")
            session.query(SkillTaxonomy).delete()
            for _, r in df.iterrows():
                session.add(SkillTaxonomy(
                    skill_name=r.get("skill_name"),
                    category=r.get("category"),
                    growth_rate_percent=float(r.get("growth_rate_percent", 0.0)),
                    demand_trend=r.get("demand_trend"),
                    obsolescence_risk=r.get("obsolescence_risk"),
                ))

        # 2. Predicted Demand
        if os.path.exists(config.OUT_PREDICTED_DEMAND):
            df = pd.read_csv(config.OUT_PREDICTED_DEMAND)
            session.query(PredictedDemand).delete()
            for _, r in df.iterrows():
                session.add(PredictedDemand(
                    skill_name=r.get("skill_name"),
                    district=r.get("district"),
                    posting_count=int(r.get("posting_count", 0)),
                    current_demand_score=float(r.get("current_demand_score", 0.0)),
                    growth_rate_percent=float(r.get("growth_rate_percent", 0.0)),
                    district_growth_rate=float(r.get("district_growth_rate", 0.0)),
                    district_skills_gap=float(r.get("district_skills_gap", 0.0)),
                    emerging_bonus=float(r.get("emerging_bonus", 0.0)),
                    obsolescence_penalty=float(r.get("obsolescence_penalty", 0.0)),
                    predicted_score_6m=float(r.get("predicted_score_6m", 0.0)),
                    confidence_6m=float(r.get("confidence_6m", 50.0)),
                    demand_band_6m=str(r.get("demand_band_6m", "Low")),
                    predicted_score_12m=float(r.get("predicted_score_12m", 0.0)),
                    confidence_12m=float(r.get("confidence_12m", 50.0)),
                    demand_band_12m=str(r.get("demand_band_12m", "Low")),
                    predicted_score_24m=float(r.get("predicted_score_24m", 0.0)),
                    confidence_24m=float(r.get("confidence_24m", 50.0)),
                    demand_band_24m=str(r.get("demand_band_24m", "Low")),
                ))

        # 3. Recommendations
        if os.path.exists(config.OUT_RECOMMENDATIONS):
            df = pd.read_csv(config.OUT_RECOMMENDATIONS)
            session.query(TrainingRecommendation).delete()
            for _, r in df.iterrows():
                session.add(TrainingRecommendation(
                    skill_name=r.get("skill_name"),
                    district=r.get("district"),
                    gap_status=r.get("gap_status"),
                    priority=r.get("priority"),
                    estimated_demand_headcount=float(r.get("estimated_demand_headcount", 0.0)),
                    available_seats=float(r.get("available_seats", 0.0)),
                    additional_seats=int(r.get("additional_seats", 0)),
                    additional_trainers=int(r.get("additional_trainers", 0)),
                    additional_labs=int(r.get("additional_labs", 0)),
                    curriculum_status=r.get("curriculum_status"),
                    confidence_12m=float(r.get("confidence_12m", 50.0)),
                    demand_band_12m=r.get("demand_band_12m"),
                ))

        # 4. District Summary
        if os.path.exists(config.OUT_DISTRICT_SUMMARY):
            df = pd.read_csv(config.OUT_DISTRICT_SUMMARY)
            session.query(DistrictSummary).delete()
            for _, r in df.iterrows():
                session.add(DistrictSummary(
                    district=r.get("district"),
                    skills_flagged=int(r.get("skills_flagged", 0)),
                    total_additional_seats=int(r.get("total_additional_seats", 0)),
                    total_additional_trainers=int(r.get("total_additional_trainers", 0)),
                    total_additional_labs=int(r.get("total_additional_labs", 0)),
                    high_priority_skills=int(r.get("high_priority_skills", 0)),
                    top_priority_skill=r.get("top_priority_skill"),
                ))

        # 5. Curriculum Alignment
        if os.path.exists(config.OUT_CURRICULUM_ALIGNMENT):
            df = pd.read_csv(config.OUT_CURRICULUM_ALIGNMENT)
            session.query(CurriculumAlignment).delete()
            for _, r in df.iterrows():
                session.add(CurriculumAlignment(
                    course_name=r.get("course_name"),
                    alignment_percent=float(r.get("alignment_percent")) if pd.notna(r.get("alignment_percent")) else None,
                    taught_skills=str(r.get("taught_skills", "")),
                    in_demand_bundle=str(r.get("in_demand_bundle", "")),
                    missing_skills=str(r.get("missing_skills", "")),
                    matched_postings=int(r.get("matched_postings", 0)),
                    note=str(r.get("note", "")),
                ))

        session.commit()
    except Exception as e:
        session.rollback()
        print(f"[sync_csv_to_db] Failed to sync data to database: {e}")
    finally:
        if should_close:
            session.close()


if __name__ == "__main__":
    init_database()
