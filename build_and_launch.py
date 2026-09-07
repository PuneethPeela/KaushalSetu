"""
build_and_launch.py
========================================================================
THIS IS THE ONLY FILE YOU NEED TO RUN.

What it does, in order:
  1. Runs the full data pipeline (Modules 1-4) on the CSVs in data/
  2. Builds the dashboard's data (Module 5)
  3. Injects that real data into the dashboard webpage
  4. Opens the finished webpage in your browser automatically

You do not need to understand Python to use this. Just run:

    python build_and_launch.py

If it doesn't open your browser automatically, it will print a file path
at the end — copy that path, paste it into your browser's address bar,
and press enter.
========================================================================
"""

import sys
import os
import json
import webbrowser

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend", "dashboard_template.html")
OUTPUT_HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "kaushalsetu-dashboard.html")
PLACEHOLDER = "__KAUSHALSETU_DATA_PLACEHOLDER__"


def main():
    print("=" * 70)
    print("KAUSHALSETU — building your dashboard from data/*.csv")
    print("=" * 70)

    print("\n[1/4] Running the data pipeline (this reads your 8 CSVs)...")
    import m4_recommendation
    m4_recommendation.run()

    print("\n[2/4] Scoring curriculum alignment...")
    import m6_curriculum_alignment
    m6_curriculum_alignment.run()

    print("\n[3/4] Preparing dashboard data...")
    import m5_dashboard_data
    data = m5_dashboard_data.run()

    print("\n[4/4] Building the website file...")
    with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
        template = f.read()

    if PLACEHOLDER not in template:
        raise RuntimeError(
            "Could not find the data placeholder in frontend/dashboard_template.html. "
            "Don't edit that file's <script id='kaushalsetu-data'> block by hand."
        )

    final_html = template.replace(PLACEHOLDER, json.dumps(data))
    with open(OUTPUT_HTML_PATH, "w", encoding="utf-8") as f:
        f.write(final_html)

    print(f"\nWebsite built: {OUTPUT_HTML_PATH}")

    print("\nOpening it in your browser now...")
    opened = False
    try:
        opened = webbrowser.open("file://" + os.path.abspath(OUTPUT_HTML_PATH))
    except Exception:
        opened = False

    print("\n" + "=" * 70)
    if opened:
        print("DONE. Your dashboard should now be open in your browser.")
    else:
        print("DONE. Couldn't auto-open a browser on this machine.")
        print("Open this file manually by double-clicking it, or pasting this")
        print("path into your browser's address bar:")
        print(f"\n    {os.path.abspath(OUTPUT_HTML_PATH)}\n")
    print("=" * 70)


if __name__ == "__main__":
    main()
