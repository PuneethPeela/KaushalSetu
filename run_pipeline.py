"""
run_pipeline.py
----------------
Runs the full KaushalSetu pipeline end to end:

    M1 Ingestion & Skill Parsing
        -> M2 Current + Predicted Demand
            -> M3 Supply & Gap Detection
                -> M4 Training Recommendations + District Summary
                -> M6 Curriculum Alignment (runs off M1's output)
                    -> M5 Dashboard Data Aggregation (reshapes everything into JSON)

Usage:
    cd kaushalsetu
    pip install -r requirements.txt
    python run_pipeline.py

All outputs land in outputs/ as CSVs (plus one dashboard_data.json), ready
to feed into the dashboard or a notebook. Each module can also be run
standalone (python src/m2_...py) if you only want to debug one stage.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import m4_recommendation
import m6_curriculum_alignment
import m5_dashboard_data


def main():
    print("=" * 70)
    print("KAUSHALSETU — Predictive Skill Demand & Training Recommendation")
    print("=" * 70)
    recommendations, district_summary = m4_recommendation.run()
    m6_curriculum_alignment.run()
    m5_dashboard_data.run()

    print("\n" + "=" * 70)
    print(f"DONE. {len(recommendations)} recommendations across "
          f"{district_summary['district'].nunique()} districts written to /outputs")
    print("outputs/dashboard_data.json is ready to drop into the dashboard.")
    print("=" * 70)


if __name__ == "__main__":
    main()

