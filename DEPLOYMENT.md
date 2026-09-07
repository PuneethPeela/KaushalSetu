# KaushalSetu — Live Web Deployment Guide

This guide walks you through deploying **KaushalSetu** as a 100% free-tier, production-ready web application on **Render** (FastAPI Web Service) with **Neon** (Serverless Postgres) and **Google Gemini Flash** (Official GenAI SDK).

---

## 1. Neon Serverless Postgres Setup (Free Tier)

Neon provides a permanent, generous free PostgreSQL database with no credit card required.

1. Go to [https://neon.tech/](https://neon.tech/) and sign up / log in with GitHub.
2. Click **Create Project**:
   - **Name**: `kaushalsetu-db`
   - **Postgres version**: 16 (default)
   - **Region**: Select closest to your users (e.g. AWS Asia Pacific / US East).
3. On the project dashboard, copy the **Connection string** (Pooled or Direct):
   ```text
   postgresql://neondb_owner:sOmEpAsSwOrD@ep-cool-fog-123456.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
4. Keep this connection string ready for the `DATABASE_URL` environment variable.

---

## 2. Google Gemini API Key (Free Tier)

KaushalSetu uses the free-tier `gemini-2.5-flash` model family to provide explainable narrative policy insights.

1. Go to [Google AI Studio](https://aistudio.google.com/).
2. Sign in with your Google account.
3. Click **Get API Key** → **Create API Key**.
4. Copy the generated key. Keep it ready for `GEMINI_API_KEY`.

---

## 3. Render Deployment (1-Click Blueprint / Web Service)

Render provides a free Web Service tier (750 hours/month) that builds and hosts Docker containers directly.

### Option A: Using Render Blueprints (Recommended)
1. Push your repository to GitHub (or use your existing repo `PuneethPeela/KaushalSetu`).
2. Log into [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** → **Blueprint**.
4. Connect your `KaushalSetu` repository. Render will detect `render.yaml` automatically.
5. Under **Environment Variables**, supply your values:
   - `DATABASE_URL`: Paste your Neon Postgres connection string from Step 1.
   - `GEMINI_API_KEY`: Paste your Google AI Studio key from Step 2.
   - `SERPAPI_KEY`: (Optional) Paste your SerpApi key for Google Trends, or leave blank to use fallback.
6. Click **Apply**. Render will build the Docker container and deploy your service!

### Option B: Manual Web Service Creation
1. Click **New +** → **Web Service**.
2. Connect your Git repository.
3. Configure settings:
   - **Name**: `kaushalsetu`
   - **Runtime**: `Docker`
   - **Instance Type**: `Free`
   - **Health Check Path**: `/api/health`
4. Add Environment Variables:
   - `DATABASE_URL` = your Neon connection string
   - `GEMINI_API_KEY` = your Gemini key
   - `SERPAPI_KEY` = your SerpApi key (optional)
5. Click **Deploy Web Service**.

> **Note on Render Free Tier Sleep Behavior:**  
> Render's free tier spins down after ~15 minutes of inactivity. When a user visits after idle time, the first request takes ~30–50 seconds to wake up. This is normal and expected on free tiers — during a hackathon demo, simply open the page a minute before your presentation so it is hot and snappy!

---

## 4. Initializing Database on Neon

Once your service is live, or from your local machine with `DATABASE_URL` set in `.env`:
```bash
python init_db.py
```
This automatically runs `Base.metadata.create_all()` and populates the database tables directly from the pipeline outputs.

---

## 5. Live Endpoints Reference

Once deployed at `https://<your-subdomain>.onrender.com`:

| Endpoint | Method | Description |
|---|---|---|
| `/` or `/dashboard` | `GET` | Live interactive web dashboard |
| `/api/health` | `GET` | Service health, DB connectivity, and Gemini status |
| `/api/dashboard-data` | `GET` | Complete aggregated pipeline JSON payload |
| `/api/pipeline/status` | `GET` | Execution status and timestamp of last run |
| `/api/pipeline/run` | `POST` | Trigger fresh pipeline run in-process |
| `/api/skills/{skill}/insight` | `GET` | Gemini Flash narrative & policy advice for skill |
| `/api/districts/{district}/insight` | `GET` | District-level workforce strategy narrative |
| `/api/simulate` | `POST` | Server-side What-If policy recalculation |

---

## 6. Local / Offline Operation (Zero Regression)

You can still run completely offline without internet, DB, or API keys:
```bash
# Standard local pipeline run (writes to outputs/*.csv)
python run_pipeline.py

# Offline dashboard builder (bakes data into static HTML file and opens browser)
python build_and_launch.py
```
Both continue to work exactly as originally designed.
