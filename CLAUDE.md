# CLAUDE.md — AFL Analytics Hub

This file provides full project context for Claude Code. Read this before making any changes.

---

## Project Overview

**afl-analytics-hub** is a full-stack AFL analytics platform whose outputs will be displayed on a modern web dashboard.

### Planned Features (in rough build order)
1. Game outcome predictions (win probability + predicted margin)
2. Brownlow vote projections
3. Live and projected ladder
4. AFL Fantasy / SuperCoach player projections
5. Live and historical fantasy scores
6. Potentially more features down the line

### Current Status (updated 2026-11-14)
- Project scaffold complete. `frontend/` is still the default create-next-app page; `backend/` has no code yet
- R exploration script written and tested (`data_pipeline/exploreFitzRoy.R`). It writes `sample_*.csv` files (gitignored)
- Elo engine: design spec and 6-task implementation plan written (see `docs/superpowers/`)
  - Task 1 done: `MatchResult` and `EloConfig` models plus pytest wiring
  - Tasks 2–6 pending: K-factor, scoring shots, MoV, engine, carryover. The plan was revised on 2026-11-14 to fix design flaws (see the plan's revision note)
  - Progress ledger: `.superpowers/sdd/progress.md`
- No database schema created yet. This is the next major task after the Elo engine

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React with Next.js (TypeScript, Tailwind CSS, App Router) |
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
│   ├── exploreFitzRoy.R        # R script exploring fitzRoy data endpoints (writes sample_*.csv)
│   ├── exploreSquiggle.py      # Empty placeholder: Squiggle exploration is paused
│   ├── pyproject.toml          # pytest config (pythonpath=".", testpaths="tests")
│   ├── requirements.R          # R package dependencies installer script
│   ├── requirements.txt        # Python data processing & modeling dependencies (incl. pytest)
│   ├── elo/                    # Layer 1 Elo engine package
│   │   ├── models.py           # MatchResult dataclass
│   │   ├── config.py           # EloConfig: all Tier-0 constants
│   │   └── (planned) k_factor.py, scoring.py, mov.py, engine.py
│   └── tests/elo/              # pytest suite for the Elo engine
│
├── docs/superpowers/           # Design specs (specs/) and implementation plans (plans/)
│                               # NOTE: currently gitignored. See "Known housekeeping" below
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
- Never commit `venv/`, `.env`, `node_modules/`, `*.csv`, `*.png`, `*.db`, `*.sqlite`

### Known housekeeping (open items)
- `.gitignore` excludes `docs/superpowers/*`, so the Elo spec and plan referenced throughout this file are **not version-controlled**. Consider removing that ignore line
- No `dev` branch exists yet, and the current branch is named `elo-engine-core` (no `feature/` prefix). See Git Branching Strategy
- `README.md` is only a title

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

### Running tests
```bash
cd ~/PersonalProjects/afl-analytics-hub/data_pipeline
source venv/bin/activate
pytest            # config in pyproject.toml; tests live in tests/
```

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
| Squiggle API | via fitzRoy `fetch_squiggle_data()` in R or direct HTTP | Fixtures, live scores, ladder, tips, standings | Free, well-documented, reliable. Exploration paused for now; fitzRoy/AFL API are the primary sources |
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

These are commented out in `exploreFitzRoy.R` with explanation.

---

## Git Branching Strategy

```
main        — always deployable, merge from dev when milestone is stable
└── dev     — primary integration branch
    ├── feature/db-schema-matches
    ├── feature/elo-engine-core          ← CURRENT WORK (actual branch name: elo-engine-core)
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
- **The developer stages and commits manually.** Don't `git add` or `git commit` unless asked

> **Actual state vs. strategy:** `dev` hasn't been created yet. Early exploration commits went to `main`,
> and `elo-engine-core` was branched from `main`. Create `dev` from `main` before merging the Elo work.

---

## Model Architecture

### Game Outcome Model (in progress)

This is WIP and flexible to change, values are just suggestions and subject to change

Two-layer architecture:

**Layer 1 — Elo Engine** (`data_pipeline/elo/` package; `EloEngine` in `engine.py`)
- Single Elo rating per team (split offensive/defensive later)
- Starting rating: 1500
- Season carryover: 72% of deviation from 1500 carries over; 28% reverts to mean — *(Tier-0 placeholder; see rationale below)*
- Variable K-factor via continuous decay curve, not stepwise bands — see K-Factor Schedule
- Venue-specific HGA (not flat) — **Venue Adjustment Index (VAI)** per team per venue
- Margin of victory multiplier with diminishing returns + autocorrelation correction — see MoV Dampening
- Scoring shots weighted more than final score (accuracy is partially random)
- **Match outcome for rating updates is judged on the adjusted margin (not the scoreboard), and is continuous.** It isn't a
  hard win/draw/loss. See Soft Match Outcome below. The scoreboard's influence is set by one dial only, `actual_score_weight` in
  the scoring-shot blend. Don't add a separate scoreboard-based W/L rule
- Input must be in chronological order. The engine doesn't sort, but it raises on out-of-order seasons or dates
- Exclude: Essendon 2016 (doping), COVID-affected 2020 rounds from *parameter optimisation* only. The engine still
  processes those matches, because other teams' ratings depend on them

> **Note on Tier-0 constants:** every numeric constant in this section is an independently-reasoned
> starting value, not an empirically fitted one. Each is tagged **Tier-0** with its own rationale.
> Real calibration against historical data happens on `feature/elo-optimisation`. See
> `docs/superpowers/specs/2026-07-11-elo-engine-differentiation-design.md` for the full reasoning
> and how these differ from the source models studied (below in Prior Art & Differentiation).

**Layer 2 — XGBoost Regression** (not yet started)
- Inputs: Elo differential, venue HGA, days rest differential, rolling EWMA stats
- Target: `home_margin` (regression)
- Win probability derived via calibrated sigmoid — not modelled separately
- Temporal cross-validation only (never shuffle — must train on past, predict future)

### Season Carryover — Tier-0
```python
carryover = 0.72   # 72% of deviation from 1500 carries into next season
reversion = 0.28   # 28% reverts to mean
```
**Rationale:** AFL list turnover between seasons is comparatively low, multi-year player contracts
and a trade/draft period that typically reshapes only a minority of any club's senior list each
off-season so a higher-than-generic carryover fraction is defensible on its own terms.

### K-Factor Schedule — Tier-0 (continuous decay, not stepwise bands)
```python
def k_factor(round_number: int) -> float:
    K_EARLY, K_LATE, TAU = 38.0, 22.0, 7.0
    return K_LATE + (K_EARLY - K_LATE) * exp(-round_number / TAU)

FINALS_K = 34.0  # fixed, not part of the decay curve
```
- `K_EARLY = 38`: round-1 reactivity — off-season roster/coaching uncertainty is high
- `K_LATE = 22`: settled, late-season value — ratings have converged
- `TAU = 7`: decay constant — curve reaches ~`K_LATE` by round 20-21
- `FINALS_K = 34`: finals sample size per team is tiny (1-4 games), so we don't want round-1-level
  reactivity, but stakes/intensity justify more than the fully-settled late-season value

### Scoring Shots Adjustment — Tier-0
```python
expected_points_per_shot = league_avg_conversion * 6 + (1 - league_avg_conversion) * 1
adjusted_score = 0.65 * (scoring_shots * expected_points_per_shot) + 0.35 * actual_score
# league_avg_conversion: fraction of scoring shots that are goals, computed by the engine
# from this project's own data, using COMPLETED PRIOR SEASONS ONLY (no look-ahead leakage).
# NOT hardcoded from a published figure. Fallback 0.50 until one season has been processed;
# can be pinned via EloConfig(league_avg_conversion=...).
# scoring_shots = goals + behinds
```
**Rationale for 65/35 (vs. an even split or heavier scoring-shot weighting):** conversion (set-shot
accuracy) has a real skill component — it isn't purely random variance — so actual score deserves
meaningful weight, not just a quarter.

**Unit note:** `league_avg_conversion` is a goal-conversion *fraction* (~0.5), not a points value, so
it's converted to `expected_points_per_shot` (goal=6, behind=1) before blending with `actual_score` —
both terms must be in points for the blend weights to mean what they say.

### Soft Match Outcome — Tier-0
```python
actual_home = 1 / (1 + exp(-adjusted_margin / outcome_scale))   # replaces hard 1 / 0.5 / 0
outcome_scale = 6.0   # one goal: ±6pt adjusted margin ≈ 0.73/0.27, ±18pt ≈ 0.95/0.05
rating_change = K * mov_multiplier * (actual_home - expected_home)
```
**Rationale:** with a hard win/loss, two near-identical close games either side of zero swing ratings in
opposite directions (about ±16 points). A logistic outcome makes close games, where scoreboard and scoring
shots most often disagree, move ratings only slightly. Example: 12.2 (74) d. 9.14 (68) has adjusted margin
−18.4, which gives an outcome of ≈0.04, so it's rated a clear loss for the scoreboard winner (9 fewer scoring shots).
**To check once real data is loaded:** how often the scoreboard winner and the adjusted-margin winner disagree.

### MoV Dampening + Autocorrelation Correction — Tier-0
```python
winner_elo_diff = elo_diff_pre_game * sign(margin)   # +ve = favourite won; 0 for a draw
mov_multiplier = (ln(1 + |margin| / S) + F) / (1 + C * max(0, winner_elo_diff))
S = 6      # AFL goal value — scales margin in "goals-equivalent" units
C = 0.0012 # autocorrelation correction strength
F = 0.5    # floor ≈ log term for a ~4pt margin, so draws/narrow results aren't weighted zero
```
Diminishing returns on margin size, plus a correction so an "expected" blowout (large pre-game Elo
gap) moves ratings less than an upset margin of the same size. Only favourite wins are dampened, and the
clamp keeps the denominator at 1 or more. The floor means a favourite held to a draw still loses rating.
(Revised 2026-11-14: the earlier `abs(elo_diff)` version dampened upsets too, and gave draws zero weight.)

**Calibration note:** with these values the multiplier is about 2–3 for typical margins, so a 41-point
adjusted win between equal teams moves ratings by about 46 points. Effective K is probably too high.
Revisit on `feature/elo-optimisation`, for example by normalising the multiplier so its historical mean is about 1. Deliberately not the well-known
FiveThirtyEight NFL Elo shape (`ln(|MOV|+1) * 2.2/(elo_diff*0.001+2.2)`) — same principle, different
scaling basis and constants, derived independently for AFL.

### Rest Feature — Tier-0
```python
# Do NOT treat rest linearly
# Any break > 10 days = is_off_bye = True (binary flag)
# Not "extra rest" — teams often come out sluggish after a bye
rest_diff = home_days_rest - away_days_rest  # both capped at 9 days
```
**Rationale for >10 (not >9):** ordinary AFL round-to-round gaps already vary between 4 and 8 days
depending on Thursday/Friday/Sunday scheduling. A >9-day cutoff risks catching normal weekend-to-weekend
gaps that aren't bye-affected; >10 days more cleanly isolates genuine bye-round gaps (typically 13+
days). The separate 9-day cap on `rest_diff` is unchanged — it limits outlier influence on the
differential feature, a different concern from identifying bye rounds.

### Features for Layer 2 (EWMA, 5-game half-life, home minus away differential)
| Feature | Source |
|---|---|
| Elo differential | Computed |
| Venue HGA (VAI) | Computed |
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
- Data source: Fryzigg (historical), AFL API (in-season), DFS Australia or other similar fan websites (in-season)

---

## Key Design Principles

1. **Data never goes to GitHub** — PostgreSQL is the source of truth; ingestion scripts recreate it
2. **R extracts, Python processes** — R writes to PostgreSQL via RPostgres; Python reads for ML
3. **Separate venvs** — `backend/` and `data_pipeline/` have independent Python environments
4. **No data leakage** — all EWMA features use `.shift(1)` / computed strictly from prior games
5. **Schema first** — always design the database schema before writing ingestion scripts
6. **Temporal CV only** — never shuffle data when cross-validating; always train on past, predict future

---

## Prior Art & Differentiation

Ideas below were studied to learn the domain. Each row states the concept taken and specifically how
this project's implementation differs — different constants (independently reasoned, not copied),
different naming, or a different formula shape. Full reasoning in
`docs/superpowers/specs/2026-07-11-elo-engine-differentiation-design.md`.

| Model | Concept Studied | How This Project Differs |
|---|---|---|
| MatterOfStats (MoSHBODS) | Separate offensive/defensive ratings; scoring shots > final score; VPVs; variable k; 6-year window | Renamed VPV → Venue Adjustment Index (VAI); own scoring-shot blend (65/35 vs. their split) and a computed-not-hardcoded conversion constant; K-factor is a continuous decay curve, not a variable-k lookup |
| Waynealytics | Two-layer Elo + XGBoost architecture; exclude bookmaker odds; venue-specific HGA | Same two-layer shape (standard, not source-specific) and same exclusion of odds; venue HGA renamed and computed independently |
| The Footycast | Pure Elo with Occam's Razor philosophy; margin → probability via calibrated sigmoid | Retained the sigmoid-calibration approach for win probability; MoV dampening formula built independently rather than adapted from any single source |
| Betfair Data Scientists | EWM rolling averages; head-to-head form; efficiency features; feature differential approach | Rolling-feature technique kept (EWMA differentials are a standard approach), specific features/half-life chosen for this project's Layer 2 |
| Betfair Brownlow Tutorial | Brownlow as ranking problem, not regression | Framing adopted; not yet designed in detail (future model) |

---

## Developer Notes

- Developer is based in Perth, WA — time zone AWST (UTC+8)
- AFL season runs approximately March to September
- "AFLM" is the competition code for AFL Men's used in fitzRoy
- Round numbers in AFL go 1-24 (home & away) + finals (QF, EF, SF, PF, GF)
- Since 2024 there is an Opening Round before Round 1. Represent it as `round_number = 0` (the K-factor curve starts at round 0)
- Note for season 2026 and onwards there is a wildcard round WC before the first week of finals. Treat it as a final (`is_final = True`)
- Finals are not numbered rounds — handle separately in all round-based logic (`MatchResult.is_final`)
- Essendon 2016 and COVID 2020 are known data anomalies — exclude from parameter optimisation
- FootyWire is blocked — do not suggest FootyWire-based solutions
- Champion Data API is not accessible — do not suggest it