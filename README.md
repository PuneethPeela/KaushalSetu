# KaushalSetu — Predictive Skill Demand & Training Recommendation Platform
*"From Skill Gaps to Future-Ready Workforce."*

🌐 **Live Deployment Link:** [https://261d432402c9cce0-122-179-43-162.serveousercontent.com](https://261d432402c9cce0-122-179-43-162.serveousercontent.com)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/PuneethPeela/KaushalSetu)

**New here / not a programmer? Read `SETUP.md` instead of this file — it's the plain-language version.**

This README is the technical reference for how the pipeline actually works.

## How to run

The simplest way — one command that does everything (pipeline + dashboard + opens browser):

```bash
pip install -r requirements.txt
python build_and_launch.py
```

### Live Google Trends data

Set a SerpApi key before running the pipeline to use the supported live
Google Trends endpoint. The key is read from the environment and is not
stored in the project:

```powershell
$env:SERPAPI_KEY = "your-serpapi-key"
python run_pipeline.py
```

Without `SERPAPI_KEY`, the project falls back to `pytrends`. That fallback is
unofficial and may receive HTTP 429 rate-limit responses; the pipeline then
uses zero live trend bonus and continues.

Or use `setup.sh` (Mac/Linux) / `setup.bat` (Windows) which does the same thing with less typing.

If you only want to run the data pipeline without touching the dashboard:

```bash
python run_pipeline.py
```

That runs Modules 1–6 in order (ingestion → demand → gap → recommendations
→ curriculum alignment → dashboard JSON) and writes every intermediate and
final table to `outputs/`, without rebuilding the HTML file. Use
`build_and_launch.py` instead if you want the actual webpage regenerated.
You can also run any module by itself for debugging:

```bash
python src/m1_ingestion.py
python src/m2_demand_prediction.py
python src/m3_supply_gap.py
python src/m4_recommendation.py
python src/m5_dashboard_data.py
```

Each one re-runs the modules before it automatically (M4 calls M3, which
calls M2, which calls M1), so you always get fresh output no matter which
file you run.

## Folder structure

```
kaushalsetu/
├── data/                          <- your 8 CSVs go here
├── outputs/                       <- generated tables + dashboard_data.json
├── src/
│   ├── config.py                  <- file paths + all tunable constants
│   ├── m1_ingestion.py            <- clean data, parse & normalize skills
│   ├── m2_demand_prediction.py    <- current demand + predictive scoring
│   ├── m3_supply_gap.py           <- training supply vs demand, gap status
│   ├── m4_recommendation.py       <- seats/trainers/labs + district rollup
│   ├── m6_curriculum_alignment.py <- course vs real co-required skills
│   └── m5_dashboard_data.py       <- reshapes M1-M4+M6 output into dashboard JSON
├── frontend/
│   └── dashboard_template.html    <- the website design (data gets injected here)
├── build_and_launch.py            <- ONE COMMAND: pipeline + dashboard + open browser
├── run_pipeline.py                <- runs just M1-M4 (no dashboard build)
├── setup.sh / setup.bat           <- one-click install + launch
├── SETUP.md                       <- plain-language setup guide, start here
└── requirements.txt
```

## What each module outputs

| Module | Output file | What's in it |
|---|---|---|
| M1 | `m1_job_postings_skills_long.csv` | One row per (job posting, skill) — the exploded/normalized skill table |
| M1 | `m1_skills_taxonomy_clean.csv` | Cleaned taxonomy reference |
| M2 | `m2_current_demand.csv` | Posting counts, avg salary, current_demand_score per (skill, district) |
| M2 | `m2_predicted_demand.csv` | Predicted score + band + confidence at 6/12/24-month horizons |
| M3 | `m3_skill_supply.csv` | Training capacity/seats/trainers per (skill, district), where mapping exists |
| M3 | `m3_skill_gap.csv` | Demand vs supply, gap_status (Critical Shortage / Shortage / Balanced / Oversupply) |
| M4 | `m4_training_recommendations.csv` | Per-skill action: additional seats, trainers, labs, curriculum status |
| M4 | `m4_district_summary.csv` | Rolled up per district — total seats/trainers/labs needed, top priority skill |
| M5 | `dashboard_data.json` | M1-M4 output reshaped into what the dashboard website reads |
| M6 | `m6_curriculum_alignment.csv` | Per course: alignment % against what employers actually co-require, missing skills |

## Read this before you present it — methodology notes

**Why there's no time-series forecasting model (no Prophet/ARIMA/LSTM).**
`job_postings_maharashtra.csv` only spans ~90 days (Jun–Sep 2026). That's
not enough history to fit a real trend model — doing so would just fit
noise and call it AI. Module 2 instead builds a **transparent multi-signal
predictive score**: current demand + skill-level growth rate (from the
taxonomy) + district-level sector growth + employer-reported skills gap +
an emerging-tech bonus + an obsolescence penalty. Every number in the score
traces back to a real column in your data — that's what "explainable AI"
(Module 15 in the original spec) means in practice here, and it's a more
defensible story for judges than a fake forecast.

**Why Module 1 doesn't use spaCy/NLP.** `skills_required` is already a
clean semicolon-separated list, not a paragraph. Real NLP would be solving
a problem this dataset doesn't have. What M1 actually does — splitting,
normalizing, and matching against the taxonomy — is still necessary and
still worth presenting; just be accurate about what it is.

**Curriculum + supply coverage gaps.** Only 16 of the 82 course names in
`training_centers_maharashtra.csv` have a matching entry in
`course_skills_mapping.csv`. For the other courses, M3 records
`supply_data_available = False` instead of guessing zero. If you present
this, say so — "supply is only mapped for courses we have curriculum data
for" is a stronger statement than an unexplained number.

**The demand→headcount conversion is an estimate, not a measurement.**
M3 converts the relative 0–130 predicted score into an estimated number of
people by scaling actual observed posting volume — there's no ground truth
headcount number in the raw data to calibrate against directly. Say this
out loud in your pitch rather than presenting it as precise.

**Tunable constants live in `config.py`**, not scattered through the code:
gap-classification thresholds, seats-per-trainer/lab ratios, and forecast
horizons. If you get real ratios (e.g. actual trainer-to-student ratios
from the training centre data) or want tighter/looser gap thresholds,
change them there — nothing else needs to be touched.

## What's in the dashboard

Seven tabs, each a stage of the pipeline: Demand Overview, Future
Prediction, Skill Gap, Recommendation, Curriculum Alignment, Districts, and
a **What-If Simulator** — drag a slider to add seats to any (skill,
district) pair and watch the gap status recompute live, right in the
browser (no server, same thresholds as `config.py`).

## Update: theming, full skill coverage, and 3-year trend context

- **Light/Dark/System theme toggle** in the sidebar. No data is persisted between sessions (no localStorage used) — it resets to Dark each time you open the file. If you want it remembered, that's a small addition (`localStorage`) you or I can add later.
- **Every skill in your data is now selectable** on the Future Prediction tab via a search box (134 skills, not a fixed top-8). Note: your data does not contain the literal tags "AI/ML" or "C++" — the closest present equivalents are Deep Learning, TensorFlow, PyTorch, NLP, Scikit-learn (for AI/ML) and nothing for C++. If your real dataset has these under those exact names, they'll appear automatically once re-ingested.
- **3-year "modeled trajectory" panel** added per skill, clearly labeled as modeled (not measured) — see the big warning comment in `m5_dashboard_data.py::build_modeled_trajectory()`. None of the 8 datasets contain real multi-year history; this back-calculates from each skill's current stated annual growth rate. Present it as illustrative context, not historical fact.
- **Axis labels added** to both the hero timeline and the Future Prediction chart (Y = relative demand score 0–100+, X = time, with a note on what solid vs. dashed means).
- **A "why this is different" strip** added to the Overview tab, summarizing the four things a generic reporting dashboard doesn't do (predicts forward, explains itself, reaches curriculum-level detail, and simulates decisions live).

## Live Web App & API Architecture (New)

KaushalSetu is equipped with a live **FastAPI** backend, **Neon Postgres** database integration, and **Google Gemini Flash** narrative intelligence:

### Running the Live Server Locally
```bash
# Start the live FastAPI server
uvicorn src.api:app --reload --port 8000
```
Open `http://localhost:8000` to interact with the live dashboard, trigger in-process pipeline re-runs, and query real-time Gemini policy narratives.

### API Endpoints
- `GET /` — Serves the live interactive dashboard web app.
- `GET /api/health` — Service health check, database status, and Gemini API readiness.
- `GET /api/dashboard-data` — Full aggregated JSON data.
- `POST /api/pipeline/run` — Executes pipeline end-to-end and updates tables.
- `GET /api/skills/{skill}/insight` — Gemini Flash explainability & policy rationale.
- `GET /api/districts/{district}/insight` — District workforce strategy brief.
- `POST /api/simulate` — Server-side What-If policy scenario simulator.

### Cloud Deployment (Render + Neon)
- See `DEPLOYMENT.md` for instructions on deploying the free-tier Docker web service on **Render** paired with serverless PostgreSQL on **Neon**.
- Render Free Tier note: Instances sleep after 15 minutes of inactivity; allow ~30–50s on initial cold start.

