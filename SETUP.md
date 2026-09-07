# KaushalSetu — Setup Guide (start here)

This guide assumes you know nothing about running code. Follow it top to bottom.

## Do you have Python installed?

1. Open a terminal (Mac: Terminal app. Windows: search "cmd" or "PowerShell").
2. Type `python3 --version` (Mac/Linux) or `python --version` (Windows) and press Enter.
3. If you see something like `Python 3.10.5`, you're set — skip to Step 1 below.
4. If you see an error, download and install Python from **python.org/downloads** first (any version 3.9 or newer), then come back here.

---

## Step 1 — Get the project onto your computer

Unzip `kaushalsetu-pipeline.zip` anywhere you like (Desktop is fine). You should see a folder called `kaushalsetu` containing `data/`, `src/`, `frontend/`, and some files like `build_and_launch.py`.

## Step 2 — Run the setup script

**Windows:** Open the `kaushalsetu` folder and double-click **`setup.bat`**.
(If Windows shows a security warning, click "More info" → "Run anyway" — this is normal for scripts you download.)

**Mac / Linux:** Open Terminal, then type these two lines one at a time:
```
cd path/to/kaushalsetu
bash setup.sh
```
(Replace `path/to/kaushalsetu` with wherever you unzipped it — you can also just type `cd ` and then drag the folder into the terminal window, which fills in the path for you.)

## Step 3 — Wait for it

You'll see some text scroll by — that's the pipeline actually processing your data. It takes a few seconds. At the end, **your browser should open automatically** showing the finished dashboard.

If your browser doesn't open by itself, look at the last few lines printed in the terminal — there's a file path there. Copy it, open your browser, paste it into the address bar, and press Enter.

---

## That's the whole thing. What did it just do?

One command (`setup.sh` / `setup.bat`) did two things:
1. Installed the only two things this project needs (`pandas`, `numpy` — for handling your data).
2. Ran `build_and_launch.py`, which processes your 8 CSVs through the full pipeline and builds the dashboard webpage with the real results already in it, then opens it.

## I want to run it again later (e.g. after changing a CSV)

You don't need to repeat Step 2's install part. Just run:
```
python3 build_and_launch.py
```
(or double-click `build_and_launch.py` if your system runs `.py` files by double-click — otherwise use the terminal command above).

## Something went wrong

- **"pip: command not found" / "python: command not found"** → Python isn't installed, or isn't on your PATH. Reinstall from python.org and make sure to check "Add Python to PATH" during installation (Windows installer shows this checkbox).
- **A red error mentioning a missing CSV file** → make sure all 8 CSVs are still inside the `data/` folder with their original names.
- **Anything else** → copy the exact error text and send it back in this chat — that's the fastest way for me to fix it for you.

| Folder / file | What it is |
|---|---|
| `data/` | Your 8 datasets |
| `src/` | The actual pipeline code (Modules 1–6 + API + Gemini insights + database models) |
| `frontend/dashboard_template.html` | The website design, with live API fetching + Gemini AI briefing |
| `src/api.py` | FastAPI server for live cloud deployment |
| `init_db.py` | Initializes and seeds database tables on Neon Postgres |
| `DEPLOYMENT.md` | Step-by-step guide for deploying on Render + Neon |
| `build_and_launch.py` | The offline script that connects everything and opens the local website |
| `outputs/` | Where all the calculated results get saved as CSVs, if you want to open them in Excel |
| `kaushalsetu-dashboard.html` | The finished offline website — created after you run setup |

You never need to edit anything to just *see* the dashboard. Only open `src/` files if you want to change how something is calculated.
