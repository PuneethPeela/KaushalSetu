"""
google_trends.py  [NEW - added for live trend signal]
------------------------------------------------------
Fetches Google Trends interest data for a list of skill names and converts
it into a bonus-score dict that M2s demand scoring formula can consume
directly.

Uses SerpApi when SERPAPI_KEY is set, which provides a supported Google
Trends endpoint. Falls back to pytrends (pip install pytrends) when no key
is configured.
Falls back gracefully to an empty dict (zero bonus for all skills) if:
  - pytrends is not installed
  - there is no internet connection
  - Google rate-limits the request
so M2 always completes even when offline.

Geo defaults to IN-MH (Maharashtra, India).
Timeframe defaults to config.TRENDS_TIMEFRAME.

How to disable entirely: set TRENDS_ENABLED = False in config.py
"""

import json
import os
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import config

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False


def _fetch_serpapi_batch(batch: list, geo: str, timeframe: str, api_key: str) -> dict:
    """Fetch one keyword batch through SerpApi's supported Trends endpoint."""
    params = urlencode({
        "engine": "google_trends",
        "q": ",".join(batch),
        "geo": geo,
        "date": timeframe,
        "api_key": api_key,
    })
    request = Request(
        f"https://serpapi.com/search.json?{params}",
        headers={"User-Agent": "KaushalSetu/1.0"},
    )
    with urlopen(request, timeout=30) as response:
        payload = json.load(response)

    if payload.get("error"):
        raise RuntimeError(payload["error"])

    totals = {skill: [] for skill in batch}
    for point in payload.get("interest_over_time", {}).get("timeline_data", []):
        for value in point.get("values", []):
            skill = value.get("query")
            if skill in totals:
                extracted_value = value.get("extracted_value")
                if extracted_value is None:
                    extracted_value = value.get("value")
                try:
                    totals[skill].append(float(extracted_value))
                except (TypeError, ValueError):
                    continue

    return {
        skill: _interest_to_bonus(sum(values) / len(values)) if values else 0
        for skill, values in totals.items()
    }


def _interest_to_bonus(score: float) -> int:
    """
    Convert a 0-100 Google Trends average interest score to a bonus point
    value on the same scale as the static emerging-tech severity bonus:
        High   (>=80) -> 15 pts
        Medium (>=50) ->  8 pts
        Low    (>=20) ->  3 pts
        None   (<20)  ->  0 pts
    """
    if score >= 80:
        return 15   # High
    if score >= 50:
        return 8    # Medium
    if score >= 20:
        return 3    # Low
    return 0


def fetch_google_trends(skills: list,
                        geo: str = None,
                        timeframe: str = None) -> dict:
    """
    Fetch Google Trends interest for each skill name in `skills`.

    Parameters
    ----------
    skills    : list of skill name strings (e.g. ["Python", "TensorFlow"])
    geo       : BCP-47 region code (default: config.TRENDS_GEO = "IN-MH")
    timeframe : pytrends timeframe string (default: config.TRENDS_TIMEFRAME)

    Returns
    -------
    dict { skill_name -> bonus_points (int 0/3/8/15) }
    Returns {} on any unrecoverable error so callers always get a valid dict.
    """
    serpapi_key = os.getenv("SERPAPI_KEY")
    if serpapi_key:
        print("[GoogleTrends] Using SerpApi live Trends endpoint.")
    if not serpapi_key and not PYTRENDS_AVAILABLE:
        print("[GoogleTrends] pytrends not installed -- run: pip install pytrends")
        print("[GoogleTrends] Falling back to zero bonus for all skills.")
        return {}

    if geo is None:
        geo = getattr(config, "TRENDS_GEO", "IN-MH")
    if timeframe is None:
        timeframe = getattr(config, "TRENDS_TIMEFRAME", "today 3-m")

    skill_bonus: dict = {}

    try:
        pytrends = None
        if not serpapi_key:
            pytrends = TrendReq(hl="en-IN", tz=330)  # tz=330 -> IST (UTC+5:30)

        # pytrends can only handle 5 keywords per request
        batch_size = 5
        batches = [skills[i:i + batch_size] for i in range(0, len(skills), batch_size)]

        print(f"[GoogleTrends] Fetching trends for {len(skills)} skills "
              f"in {len(batches)} batch(es)  (geo={geo}, timeframe={timeframe}) ...")

        for idx, batch in enumerate(batches):
            try:
                if serpapi_key:
                    skill_bonus.update(_fetch_serpapi_batch(batch, geo, timeframe, serpapi_key))
                else:
                    pytrends.build_payload(batch, geo=geo, timeframe=timeframe)
                    df = pytrends.interest_over_time()

                    if df.empty:
                        for skill in batch:
                            skill_bonus[skill] = 0
                    else:
                        for skill in batch:
                            if skill in df.columns:
                                avg_interest = df[skill].mean()
                                skill_bonus[skill] = _interest_to_bonus(float(avg_interest))
                            else:
                                skill_bonus[skill] = 0

                # Polite delay between batches to avoid Google rate-limiting (429)
                # 4 sec is safer for 27 batches — total ~1.8 min but no dropped batches
                if idx < len(batches) - 1:
                    time.sleep(4)

            except Exception as batch_err:
                print(f"[GoogleTrends] Batch {idx + 1}/{len(batches)} failed "
                      f"({batch_err}) -- using 0 bonus for: {batch}")
                for skill in batch:
                    skill_bonus[skill] = 0

        non_zero = sum(1 for v in skill_bonus.values() if v > 0)
        print(f"[GoogleTrends] Done. {non_zero}/{len(skills)} skills have a non-zero trend bonus.")

    except Exception as e:
        print(f"[GoogleTrends] Connection failed: {e}")
        print("[GoogleTrends] Falling back to zero bonus for all skills.")
        return {}

    return skill_bonus
