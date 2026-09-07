"""
config.py
---------
One place for file paths and tunable constants. If you rename a CSV or move
the data folder, this is the only file you should need to touch.
"""

import os

# Root of the project = one level up from src/
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ---- Input files (must match filenames inside DATA_DIR) ----
FILE_JOB_POSTINGS = os.path.join(DATA_DIR, "job_postings_maharashtra.csv")
FILE_SKILLS_TAXONOMY = os.path.join(DATA_DIR, "skills_taxonomy_india.csv")
FILE_TRAINING_CENTERS = os.path.join(DATA_DIR, "training_centers_maharashtra.csv")
FILE_TRAINING_OUTCOMES = os.path.join(DATA_DIR, "training_participants_outcomes.csv")
FILE_SECTOR_GROWTH = os.path.join(DATA_DIR, "industry_demand_sector_growth.csv")
FILE_EMERGING_TECH = os.path.join(DATA_DIR, "emerging_technology_trends.csv")
FILE_COURSE_SKILLS = os.path.join(DATA_DIR, "course_skills_mapping.csv")
FILE_DISTRICT_PLANS = os.path.join(DATA_DIR, "district_training_plans.csv")

# ---- Module 1 output ----
OUT_SKILL_DEMAND_LONG = os.path.join(OUTPUT_DIR, "m1_job_postings_skills_long.csv")
OUT_SKILLS_TAXONOMY_CLEAN = os.path.join(OUTPUT_DIR, "m1_skills_taxonomy_clean.csv")

# ---- Module 2 output ----
OUT_CURRENT_DEMAND = os.path.join(OUTPUT_DIR, "m2_current_demand.csv")
OUT_PREDICTED_DEMAND = os.path.join(OUTPUT_DIR, "m2_predicted_demand.csv")

# ---- Module 3 output ----
OUT_SUPPLY = os.path.join(OUTPUT_DIR, "m3_skill_supply.csv")
OUT_GAP = os.path.join(OUTPUT_DIR, "m3_skill_gap.csv")

# ---- Module 4 output ----
OUT_RECOMMENDATIONS = os.path.join(OUTPUT_DIR, "m4_training_recommendations.csv")
OUT_DISTRICT_SUMMARY = os.path.join(OUTPUT_DIR, "m4_district_summary.csv")

# ---- Module 5 output ----
OUT_DASHBOARD_DATA = os.path.join(OUTPUT_DIR, "dashboard_data.json")

# ---- Module 6 output ----
OUT_CURRICULUM_ALIGNMENT = os.path.join(OUTPUT_DIR, "m6_curriculum_alignment.csv")

# ---- Forecast horizons (months) ----
HORIZONS = [6, 12, 24]

# ---- Gap classification thresholds ----
# ratio = demand_units / supply_units
GAP_CRITICAL_RATIO = 1.8   # demand >= 1.8x supply
GAP_SHORTAGE_RATIO = 1.15  # demand >= 1.15x supply
GAP_OVERSUPPLY_RATIO = 0.7 # demand <= 0.7x supply -> oversupplied

# ---- Resourcing rules used in Module 4 (tune these to real ratios if you have them) ----
SEATS_PER_TRAINER = 60
SEATS_PER_LAB = 300

# ---- Google Trends settings (used by google_trends.py + Module 2) ----
# Set TRENDS_ENABLED = False to skip the live fetch and run fully offline.
TRENDS_ENABLED   = True
TRENDS_GEO       = "IN-MH"       # Maharashtra, India  (BCP-47 region code)
TRENDS_TIMEFRAME = "today 3-m"   # last 3 months of search interest data
