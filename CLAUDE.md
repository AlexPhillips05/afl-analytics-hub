# CLAUDE.md — AFL Analytics Hub

This file provides full project context for Claude Code. Read this before making any changes.

---

## Project Overview

**afl-analytics-hub** is a full-stack AFL analytics platform that will be displayed on a modern web dashboard

### Planned Features (in rough build order)
1. Game outcome predictions (win probability + predicted margin)
2. Brownlow vote projections
3. Live and projected ladder
4. AFL Fantasy / SuperCoach player projections
5. Live and historical fantasy scores
6. Potentially more features down the line

### Current Status
- Project scaffold complete
- R exploration script written and tested (`data_pipeline/explore.R`)
- Elo engine design has begin, implementation starting on `feature/elo-engine-core` branch
- No database schema created yet

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (TypeScript, Tailwind CSS, App Router) |
| Frontend ORM | Drizzle ORM + postgres.js |
| Backend API | Python FastAPI + uvicorn |
| ML / Data Pipeline | Python (scikit-learn, XGBoost, pandas, numpy) |
| Data Extraction | R + fitzRoy package |
| Database | PostgreSQL (native WSL2 Ubuntu install) |
| Environment | WSL2 Ubuntu 24.04, VS Code |

### Key Package Versions
- Next.js: 16.x (create-next-app@16.2.9)
- Python: system Python3 (WSL2 Ubuntu)
- R: 4.3.3 ("Angel Food Cake")
- fitzRoy: latest (installed via R console)
- drizzle-orm + postgres: installed in frontend/
- drizzle-kit: installed as dev dependency in frontend/

---

## Repository Structure

```
afl-analytics-hub/
├── .gitignore                  # Main ignore file (covers venv/, .env, node_modules/, etc.)
├── README.md                   # Main project introduction
├── CLAUDE.md                   # Overall project development description, references & commands
│
├── backend/                    # FastAPI — serves predictions as JSON
│   └── requirements.txt        # Backend python dependencies
│
├── data_pipeline/              # R extraction + Python processing + ML models
│   ├── .lintr.R                # Linter configuration for R scripts
│   ├── exploreFitzRoy.R        # R script exploring fitzRoy data endpoints
│   ├── exploreSquiggle.py      # Python script exploring the Squiggle API
│   ├── requirements.R          # R package dependencies installer script
│   └── requirements.txt        # Python data processing & modeling dependencies
│
└── frontend/                   # Next.js application
    ├── app/                    # Next.js App Router pages, layouts, and styles
    │   ├── favicon.ico
    │   ├── globals.css
    │   ├── layout.tsx
    │   └── page.tsx
    ├── public/                 # Static SVG assets (file, globe, next, vercel, window)
    ├── .gitignore              # Frontend-specific gitignore rules
    ├── AGENTS.md               # Frontend AI Agent collaboration guidelines
    ├── CLAUDE.md               # Frontend development references & commands
    ├── README.md               # Frontend local setup guide
    ├── eslint.config.mjs       # Linting configurations
    ├── next.config.ts          # Next.js compiler settings
    ├── package-lock.json
    ├── package.json            # Script definitions and npm dependencies
    ├── postcss.config.mjs      # Tailwind CSS styling setup
    └── tsconfig.json           # TypeScript compilation configurations
```

### Important Directory Rules
- All ML model logic lives in `data_pipeline/` — NOT in `backend/`
- `backend/` is only for FastAPI routes that serve already-computed predictions
- R scripts live in `data_pipeline/` — the R venv concept does not apply (R packages are system-wide)
- Never commit `venv/`, `.env`, `node_modules/`, `*.csv`, `*.db`, `*.sqlite`

---

## Python Virtual Environments

There are two separate venvs. Always activate the correct one before installing packages or running scripts.

```bash
# Data pipeline (pandas, scikit-learn, ML packages)
cd ~/PersonalProjects/afl-analytics-hub/data_pipeline
source venv/bin/activate

# Backend (FastAPI, uvicorn, psycopg2)
cd ~/PersonalProjects/afl-analytics-hub/backend
source venv/bin/activate
```

R packages are system-wide (not in a venv). R package dependencies are documented in `data_pipeline/requirements.R`.

---

## Database

- **Engine:** PostgreSQL running natively in WSL2 Ubuntu
- **Database name:** `afl_analytics`
- **User:** `afl_user`
- **Connection string:** `postgresql://afl_user:<password>@localhost:5432/afl_analytics`
- Connection string lives in `.env` files — never hardcoded

### Starting PostgreSQL
```bash
sudo service postgresql start
```

### Schema Design/Status
Not yet created. Design is likely the next major task after the Elo engine.

---

## Data Sources

| Source | Access Method | Used For | Notes |
|---|---|---|---|
| fitzRoy (R package) | `library(fitzRoy)` | Historical match results, player stats, fixtures, ladder | Primary extraction tool |
| Fryzigg API | via fitzRoy `fetch_player_stats_fryzigg()` | Rich historical player stats (81 columns) | Does NOT update in-season — training data only |
| Squiggle API | via fitzRoy`fetch_squiggle_data()` in R or direct HTTP | Fixtures, live scores, ladder, tips, standings | Free, well-documented, reliable |
| AFL official API | `aflapi.afl.com.au/afl/v2/` | Fixtures, results, ladder | Undocumented, can break without notice, could be used for live data? |
| FootyWire | Previously via fitzRoy | Player stats | **BLOCKED** — FootyWire now blocks automated scraping via ModSecurity/Cloudflare. Do not attempt. |
| Champion Data API | Commercial only | Full live player stats | Restricted to AFL-accredited organisations — not accessible |

### FootyWire Note
All FootyWire-based fitzRoy functions are **non-functional** due to Cloudflare blocking. These include:
- `fetch_fantasy_scores()`
- `fetch_supercoach_scores()`
- `fetch_betting_odds_footywire()`
- `fetch_awards_brownlow()`
- `fetch_rising_star()`
- `fetch_outofcontract()`

These are commented out in `explore.R` with explanation.

---

## Git Branching Strategy

```
main        — always deployable, merge from dev when milestone is stable
└── dev     — primary integration branch
    ├── feature/db-schema-matches
    ├── feature/elo-engine-core          ← CURRENT BRANCH
    ├── feature/elo-venue-hga
    ├── feature/elo-optimisation
    ├── feature/rolling-features
    ├── feature/xgboost-model
    └── ...
```

### Rules
- Never commit directly to `main` or `dev`
- Branch naming: `feature/`, `fix/`, `chore/`
- Each branch = one discrete unit of work (1-3 days max)
- Always branch off `dev`, merge back to `dev`
- Merge `dev` → `main` only when a full milestone is working and tested

---

## Model Architecture

### Game Outcome Model (in progress)

This is WIP and flexible to change, values are just suggestions and subject to change

Two-layer architecture:

**Layer 1 — Elo Engine** (`data_pipeline/elo/elo_engine.py`)
- Single Elo rating per team (split offensive/defensive later)
- Starting rating: 1500
- Season carryover: 65% of deviation from 1500 carries over; 35% reverts to mean
- Variable K-factor: higher early in season, lower late season
- Venue-specific HGA (not flat) — Venue Performance Values (VPVs) per team per venue
- Margin of victory multiplier with diminishing returns + autocorrelation correction
- Scoring shots weighted more than final score (accuracy is partially random)
- Exclude: Essendon 2016 (doping), COVID-affected 2020 rounds from parameter optimisation

**Layer 2 — XGBoost Regression** (not yet started)
- Inputs: Elo differential, venue HGA, days rest differential, rolling EWMA stats
- Target: `home_margin` (regression)
- Win probability derived via calibrated sigmoid — not modelled separately
- Temporal cross-validation only (never shuffle — must train on past, predict future)

### K-Factor Schedule
```python
Finals:        36.0
Rounds 1-6:    40.0   # High — Elo needs to react fast early
Rounds 7-13:   32.0
Rounds 14-20:  28.0
Rounds 21+:    24.0   # Late season — ratings are settled
```

### Scoring Shots Adjustment
```python
adjusted_score = 0.75 * (scoring_shots * league_avg_conversion) + 0.25 * actual_score
# league_avg_conversion ≈ 0.53 historically (tunable parameter)
# scoring_shots = goals + behinds
```

### Rest Feature
```python
# Do NOT treat rest linearly
# Any break > 9 days = is_off_bye = True (binary flag)
# Not "extra rest" — teams often come out sluggish after a bye
rest_diff = home_days_rest - away_days_rest  # both capped at 9 days
```

### Features for Layer 2 (EWMA, 5-game half-life, home minus away differential)
| Feature | Source |
|---|---|
| Elo differential | Computed |
| Venue HGA (VPV) | Computed |
| Days rest differential (capped) | fetch_fixture() |
| is_off_bye (home), is_off_bye (away) | fetch_fixture() |
| Rolling scoring margin | fetch_results() |
| Rolling win rate | fetch_results() |
| Inside 50s differential | fetch_team_stats() |
| Contested possessions differential | fetch_team_stats() |
| I50/R50 efficiency | fetch_team_stats() |
| Clearances differential | fetch_team_stats() |
| Kicking efficiency (goals / scoring shots) | fetch_results() |

### Exclusions (deliberate)
- **No bookmaker odds** — model independence
- **No individual player stats in tipping outcome model** — team aggregates are more robust and available earlier
- **No weather data** — tested by community, noisy with low marginal predictive lift

### Evaluation Metrics
- The values are subject to change and are placeholder for now
- MAE (target: < 28 points)
- Tipping accuracy (target: > 67%)
- Bits score (Monash probabilistic metric — rewards calibrated probabilities)
- Benchmarked against Squiggle leaderboard

### Historical Data Range
- **Elo initialisation:** Pull data from 2000 to warm up ratings
- **Model training:** 2010 to present
- **Rationale:** Ratings well-calibrated by 2010; avoids cold-start noise
- This might not be possible depending on data sources and how far back they have data

---

## Future Models (not started)

### Brownlow Vote Projections
- Completely separate model from outcome model
- Fundamentally a player-game ranking problem, not regression
- Key stats: disposal quality, contested possessions, clearances, inside 50s
- Note: umpire biases are significant and must be modelled
- Data source: `fetch_coaches_votes()`, Fryzigg player stats

### AFL Fantasy / SuperCoach Projections
- Estimate per-player statistical output per game
- Apply Fantasy/SuperCoach scoring formula to projected stats
- Requires: player-level historical stats, opposition matchup data, team game plan model
- Data source: Fryzigg (historical), AFL API (in-season), DFS Austrlia or other similar fan websites (in-season)

---

## Key Design Principles

1. **Data never goes to GitHub** — PostgreSQL is the source of truth; ingestion scripts recreate it
2. **R extracts, Python processes** — R writes to PostgreSQL via RPostgres; Python reads for ML
3. **Separate venvs** — `backend/` and `data_pipeline/` have independent Python environments
4. **No data leakage** — all EWMA features use `.shift(1)` / computed strictly from prior games
5. **Schema first** — always design the database schema before writing ingestion scripts
6. **Temporal CV only** — never shuffle data when cross-validating; always train on past, predict future

---

## References & Community Models Studied

| Model | Key Insight Used |
|---|---|
| MatterOfStats (MoSHBODS) | Separate offensive/defensive ratings; scoring shots > final score; VPVs; variable k; 6-year window |
| Waynealytics | Two-layer Elo + XGBoost architecture; exclude bookmaker odds; venue-specific HGA |
| The Footycast | Pure Elo with Occam's Razor philosophy; margin → probability via calibrated sigmoid |
| Betfair Data Scientists | EWM rolling averages; head-to-head form; efficiency features; feature differential approach |
| Betfair Brownlow Tutorial | Brownlow as ranking problem, not regression |

---

## Developer Notes

- Developer is based in Perth, WA — time zone AWST (UTC+8)
- AFL season runs approximately March to September
- "AFLM" is the competition code for AFL Men's used in fitzRoy
- Round numbers in AFL go 1-24 (home & away) + finals (QF, EF, SF, PF, GF)
- Note for season 2026 and onwards there is a wildcard round WC before the first week of finals
- Finals are not numbered rounds — handle separately in all round-based logic
- Essendon 2016 and COVID 2020 are known data anomalies — exclude from parameter optimisation
- FootyWire is blocked — do not suggest FootyWire-based solutions
- Champion Data API is not accessible — do not suggest it