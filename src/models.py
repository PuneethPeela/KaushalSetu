"""
src/models.py
-------------
SQLAlchemy declarative models for KaushalSetu.
Mirrors output tables from Modules 1-6, plus Gemini AI insight caching
and pipeline execution history.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, Index
)
from db import Base


class JobPostingSkill(Base):
    __tablename__ = "m1_job_postings_skills_long"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(100), index=True)
    skill_name = Column(String(200), index=True)
    in_taxonomy = Column(Boolean, default=False)
    district = Column(String(100), index=True)
    industry = Column(String(200))
    job_title = Column(String(255))
    experience_required = Column(String(100))
    salary_offered = Column(Float, nullable=True)
    posted_date = Column(DateTime, nullable=True)
    job_type = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class SkillTaxonomy(Base):
    __tablename__ = "m1_skills_taxonomy_clean"

    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_name = Column(String(200), unique=True, index=True)
    category = Column(String(200), nullable=True)
    growth_rate_percent = Column(Float, default=0.0)
    demand_trend = Column(String(50), nullable=True)
    obsolescence_risk = Column(String(50), nullable=True)


class CurrentDemand(Base):
    __tablename__ = "m2_current_demand"

    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_name = Column(String(200), index=True)
    district = Column(String(100), index=True)
    posting_count = Column(Integer, default=0)
    avg_salary = Column(Float, nullable=True)
    in_taxonomy = Column(Boolean, default=False)
    current_demand_score = Column(Float, default=0.0)

    __table_args__ = (
        Index("idx_curr_demand_skill_dist", "skill_name", "district"),
    )


class PredictedDemand(Base):
    __tablename__ = "m2_predicted_demand"

    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_name = Column(String(200), index=True)
    district = Column(String(100), index=True)
    posting_count = Column(Integer, default=0)
    current_demand_score = Column(Float, default=0.0)
    growth_rate_percent = Column(Float, default=0.0)
    district_growth_rate = Column(Float, default=0.0)
    district_skills_gap = Column(Float, default=0.0)
    emerging_bonus = Column(Float, default=0.0)
    obsolescence_penalty = Column(Float, default=0.0)
    predicted_score_6m = Column(Float, default=0.0)
    confidence_6m = Column(Float, default=50.0)
    demand_band_6m = Column(String(50), default="Low")
    predicted_score_12m = Column(Float, default=0.0)
    confidence_12m = Column(Float, default=50.0)
    demand_band_12m = Column(String(50), default="Low")
    predicted_score_24m = Column(Float, default=0.0)
    confidence_24m = Column(Float, default=50.0)
    demand_band_24m = Column(String(50), default="Low")

    __table_args__ = (
        Index("idx_pred_demand_skill_dist", "skill_name", "district"),
    )


class SkillSupply(Base):
    __tablename__ = "m3_skill_supply"

    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_name = Column(String(200), index=True)
    district = Column(String(100), index=True)
    total_capacity = Column(Integer, default=0)
    available_seats = Column(Integer, default=0)
    total_trainers = Column(Integer, default=0)
    avg_placement_rate = Column(Float, default=0.0)
    course_count = Column(Integer, default=0)


class SkillGap(Base):
    __tablename__ = "m3_skill_gap"

    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_name = Column(String(200), index=True)
    district = Column(String(100), index=True)
    estimated_demand_headcount = Column(Float, default=0.0)
    available_seats = Column(Float, default=0.0)
    gap_ratio = Column(Float, nullable=True)
    gap_units = Column(Float, default=0.0)
    gap_status = Column(String(100), index=True)


class TrainingRecommendation(Base):
    __tablename__ = "m4_training_recommendations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    skill_name = Column(String(200), index=True)
    district = Column(String(100), index=True)
    gap_status = Column(String(100))
    priority = Column(String(50), index=True)
    estimated_demand_headcount = Column(Float, default=0.0)
    available_seats = Column(Float, default=0.0)
    additional_seats = Column(Integer, default=0)
    additional_trainers = Column(Integer, default=0)
    additional_labs = Column(Integer, default=0)
    curriculum_status = Column(String(255))
    confidence_12m = Column(Float, default=50.0)
    demand_band_12m = Column(String(50), default="Low")


class DistrictSummary(Base):
    __tablename__ = "m4_district_summary"

    id = Column(Integer, primary_key=True, autoincrement=True)
    district = Column(String(100), unique=True, index=True)
    skills_flagged = Column(Integer, default=0)
    total_additional_seats = Column(Integer, default=0)
    total_additional_trainers = Column(Integer, default=0)
    total_additional_labs = Column(Integer, default=0)
    high_priority_skills = Column(Integer, default=0)
    top_priority_skill = Column(String(200), nullable=True)


class CurriculumAlignment(Base):
    __tablename__ = "m6_curriculum_alignment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_name = Column(String(255), unique=True, index=True)
    alignment_percent = Column(Float, nullable=True)
    taught_skills = Column(Text, nullable=True)
    in_demand_bundle = Column(Text, nullable=True)
    missing_skills = Column(Text, nullable=True)
    matched_postings = Column(Integer, default=0)
    note = Column(Text, nullable=True)


class AIInsightCache(Base):
    __tablename__ = "ai_insights_cache"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cache_key = Column(String(255), unique=True, index=True)  # e.g., "skill:Python:Pune:Shortage:12"
    insight_type = Column(String(50), index=True)            # "skill" or "district"
    narrative = Column(Text, nullable=False)
    recommendations_summary = Column(Text, nullable=True)
    model_used = Column(String(100), default="gemini-2.5-flash")
    is_fallback = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String(50), default="COMPLETED")
    postings_count = Column(Integer, default=0)
    skills_count = Column(Integer, default=0)
    districts_count = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    duration_seconds = Column(Float, default=0.0)
