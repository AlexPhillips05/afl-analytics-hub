# data_pipeline/fetch_player_stats.R
# Fetch every AFL player-match stat line from 2000 to the current year from AFL Tables and land the
# raw rows in raw_afltables_player_stats (~240k rows). Values are untouched (columns are only selected
# and renamed to snake_case); data_pipeline/load_team_stats.py sums them into team_match_stats.
#
# The table is owned by Prisma (database/): this script only replaces rows (see db_connection.R).
#
# Run from the repo root:  Rscript data_pipeline/fetch_player_stats.R

suppressPackageStartupMessages(library(fitzRoy))
source("data_pipeline/db_connection.R")

first_season <- 2000
last_season <- as.integer(format(Sys.Date(), "%Y"))

# fitzRoy/AFL Tables column -> raw_afltables_player_stats column
raw_columns <- c(
  Season = "season", Round = "round", Date = "date", Venue = "venue",
  Home.team = "home_team", Away.team = "away_team", Playing.for = "playing_for",
  ID = "player_id", First.name = "first_name", Surname = "surname",
  Kicks = "kicks", Marks = "marks", Handballs = "handballs", Disposals = "disposals",
  Goals = "goals", Behinds = "behinds", Hit.Outs = "hit_outs", Tackles = "tackles",
  Rebounds = "rebounds", Inside.50s = "inside_50s", Clearances = "clearances", Clangers = "clangers",
  Frees.For = "frees_for", Frees.Against = "frees_against", Brownlow.Votes = "brownlow_votes",
  Contested.Possessions = "contested_possessions", Uncontested.Possessions = "uncontested_possessions",
  Contested.Marks = "contested_marks", Marks.Inside.50 = "marks_inside_50",
  One.Percenters = "one_percenters", Bounces = "bounces", Goal.Assists = "goal_assists",
  Time.on.Ground = "time_on_ground", Substitute = "substitute"
)

cat(sprintf("Fetching AFL Tables player stats %d-%d...\n", first_season, last_season))
players <- fetch_player_stats_afltables(season = first_season:last_season)
players <- players[players$Season >= first_season & players$Season <= last_season, names(raw_columns)]
names(players) <- unname(raw_columns)

con <- connect_db()
on.exit(dbDisconnect(con))
replace_table_rows(con, "raw_afltables_player_stats", as.data.frame(players))
cat(sprintf("Wrote %d player-match rows (%d seasons) to raw_afltables_player_stats\n",
            nrow(players), length(unique(players$season))))
