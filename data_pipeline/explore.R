# data_pipeline/explore.R
# temporary script to explore the fitzRoy package and fetch some AFL data

# Load libraries quietly (removes startup messages)
suppressPackageStartupMessages({
  library(fitzRoy)
  library(dplyr)
  library(readr)
})

cat("Fetching AFL Data using fitzRoy...\n")

# 1. Fetch Fixture Data (2025 Season)
cat("1. Fetching Fixture...\n")
fixture_2025 <- fetch_fixture(2025, comp = "AFLM")
write_csv(fixture_2025, "data_pipeline/sample_fixture.csv")

# 2. Fetch Match Results (2025 Season)
cat("2. Fetching Results...\n")
results_2025 <- fetch_results(2025, comp = "AFLM")
write_csv(results_2025, "data_pipeline/sample_results.csv")

# 3. Fetch a Ladder (2025, Round 24)
cat("3. Fetching Ladder...\n")
ladder_2025_rd24 <- fetch_ladder(2025, round_number = 24, comp = "AFLM")
write_csv(ladder_2025_rd24, "data_pipeline/sample_ladder.csv")

# 4. Fetch Player Stats (2025, Round 1)
cat("4. Fetching Player Stats (Round 1 only)...\n")
player_stats_rd1 <- fetch_player_stats(2025, round_number = 1, comp = "AFLM")
write_csv(player_stats_rd1, "data_pipeline/sample_player_stats.csv")

# 5. Fetch Lineup Data (2025, Round 1)
cat("5. Fetching Lineups (Round 1 only)...\n")
lineups_rd1 <- fetch_lineup(2025, round_number = 1, comp = "AFLM")
write_csv(lineups_rd1, "data_pipeline/sample_lineups.csv")

# 6. Fetch Team Stats (2025, Round 1)
cat("6. Fetching Team Stats (Round 1 only)...\n")
team_stats_rd1 <- fetch_team_stats(2025, round_number = 1, comp = "AFLM")
write_csv(team_stats_rd1, "data_pipeline/sample_team_stats.csv")

# 7. Fetch Player Details (Current)
cat("7. Fetching Player Details (Fremantle)...\n")
player_details <- fetch_player_details(
  team = "Fremantle",
  current = TRUE,
  comp = "AFLM",
  official_teams = TRUE
)
write_csv(player_details, "data_pipeline/sample_player_details.csv")

#TODO: Explore other functions at https://github.com/jimmyday12/fitzRoy/tree/main/R
#TODO: Explore Squiggle and Fryzigg later too!!

cat("Done! Check the data_pipeline folder for your CSV files.\n")
