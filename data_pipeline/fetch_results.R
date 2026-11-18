# data_pipeline/fetch_results.R
# Fetch every AFL match result from 2000 to the current year from AFL Tables and land the raw rows
# in the raw_afltables_results table. Values are untouched (columns are only renamed to snake_case);
# data_pipeline/load_matches.py turns them into clean matches.
#
# The table is owned by Prisma (database/): this script only replaces rows (see db_connection.R).
#
# Run from the repo root:  Rscript data_pipeline/fetch_results.R

suppressPackageStartupMessages(library(fitzRoy))
source("data_pipeline/db_connection.R")

first_season <- 2000
last_season <- as.integer(format(Sys.Date(), "%Y"))

# fitzRoy/AFL Tables column -> raw_afltables_results column
raw_columns <- c(
  Game = "game", Date = "date", Season = "season", Round = "round", Round.Type = "round_type",
  Round.Number = "round_number", Home.Team = "home_team", Home.Goals = "home_goals",
  Home.Behinds = "home_behinds", Home.Points = "home_points", Away.Team = "away_team",
  Away.Goals = "away_goals", Away.Behinds = "away_behinds", Away.Points = "away_points",
  Venue = "venue", Margin = "margin"
)

cat(sprintf("Fetching AFL Tables results %d-%d...\n", first_season, last_season))
results <- fetch_results_afltables(first_season:last_season)
results <- results[results$Season >= first_season & results$Season <= last_season, names(raw_columns)]
names(results) <- unname(raw_columns)

con <- connect_db()
on.exit(dbDisconnect(con))
replace_table_rows(con, "raw_afltables_results", results)
cat(sprintf("Wrote %d matches (%d seasons) to raw_afltables_results\n",
            nrow(results), length(unique(results$season))))
