# data_pipeline/explore.R
# temporary script to explore the fitzRoy package and fetch some AFL data

# Load the libraries
library(fitzRoy)
library(dplyr)
library(readr)

print("Fetching AFL Data using fitzRoy...")

# 1. Fetch Fixture Data (2023 Season)
# This gives you match times, venues, rounds, and team names.
print("1. Fetching Fixture...")
fixture_2023 <- fetch_fixture(2023, comp = "AFLM")
write_csv(fixture_2023, "data_pipeline/sample_fixture.csv")

# 2. Fetch Match Results (2023 Season)
# This gives you final scores, margins, and basic match details.
print("2. Fetching Results...")
results_2023 <- fetch_results(2023, comp = "AFLM")
write_csv(results_2023, "data_pipeline/sample_results.csv")

# 3. Fetch a Ladder (2023, Round 24)
# Gives you the final ladder of the season, including percentage, points for/against.
print("3. Fetching Ladder...")
ladder_2023_rd24 <- fetch_ladder(2023, round_number = 24, comp = "AFLM")
write_csv(ladder_2023_rd24, "data_pipeline/sample_ladder.csv")

# 4. Fetch Player Stats (2023, Round 1)
# WARNING: Player stats datasets are massive. We will just grab Round 1 to look at the columns.
print("4. Fetching Player Stats (Round 1 only)...")
player_stats_rd1 <- fetch_player_stats(2023, round_number = 1, comp = "AFLM")
write_csv(player_stats_rd1, "data_pipeline/sample_player_stats.csv")

print("Done! Check the data_pipeline folder for your CSV files.")
