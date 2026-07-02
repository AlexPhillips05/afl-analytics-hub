# data_pipeline/explore.R
# temporary script to explore the fitzRoy package and fetch some AFL data

# Load libraries quietly (removes startup messages)
suppressPackageStartupMessages({
  library(fitzRoy)
  library(dplyr)
  library(readr)
  library(ggplot2)
})

cat("Fetching AFL Data using fitzRoy...\n")

# 1. Fetch Fixture Data (2025 Season)
# NOTE: fetch_fixture_afl, fetch_fixture_footywire, fetch_fixture_squiggle also can be used
cat("1. Fetching Fixture...\n")
fixture_2025 <- fetch_fixture(2025, comp = "AFLM")
write_csv(fixture_2025, "data_pipeline/sample_fixture.csv")

# 2. Fetch Match Results (2025 Season)
# NOTE: fetch_results_afl, fetch_results_afltables, fetch_results_footywire, fetch_results_squiggle also can be used
cat("2. Fetching Results...\n")
results_2025 <- fetch_results(2025, comp = "AFLM")
write_csv(results_2025, "data_pipeline/sample_results.csv")

# 3. Fetch a Ladder (2025, Round 24)
# NOTE: fetch_ladder_afl, fetch_ladder_afltables, fetch_ladder_squiggle also can be used
cat("3. Fetching Ladder...\n")
ladder_2025_rd24 <- fetch_ladder(2025, round_number = 24, comp = "AFLM")
write_csv(ladder_2025_rd24, "data_pipeline/sample_ladder.csv")

# 4. Fetch Player Stats (2025, Round 1)
# NOTE: fetch_player_stats_afl, fetch_player_stats_afltables, fetch_player_stats_footywire, fetch_player_stats_fryzigg also can be used
cat("4. Fetching Player Stats (Round 1 only)...\n")
player_stats_rd1 <- fetch_player_stats(2025, round_number = 1, comp = "AFLM")
write_csv(player_stats_rd1, "data_pipeline/sample_player_stats.csv")

# 5. Fetch Lineup Data (2025, Round 1)
# NOTE: fetch_lineup_afl also can be used
cat("5. Fetching Lineups (Round 1 only)...\n")
lineups_rd1 <- fetch_lineup(2025, round_number = 1, comp = "AFLM")
write_csv(lineups_rd1, "data_pipeline/sample_lineups.csv")

# 6. Fetch Team Stats (2025, Round 1)
cat("6. Fetching Team Stats (Round 1 only)...\n")
team_stats_rd1 <- fetch_team_stats(2025, round_number = 1, comp = "AFLM")
write_csv(team_stats_rd1, "data_pipeline/sample_team_stats.csv")

# 7. Fetch Player Details (Current)
# NOTE: fetch_player_details_afl, fetch_player_details_afltables, fetch_player_details_footywire also can be used
cat("7. Fetching Player Details (Fremantle)...\n")
player_details <- fetch_player_details(
  team = "Fremantle",
  current = TRUE,
  comp = "AFLM",
  official_teams = TRUE
)
write_csv(player_details, "data_pipeline/sample_player_details.csv")

# 8. Fetch Coaches Votes (2025)
#NOTE: calculate_coaches_vote_possibilities() returns all possible breakdowns of coaches votes between two coaches, given said votes.
cat("8. Fetching Coaches Votes (2025)...\n")
coaches_votes <- fetch_coaches_votes(2025, comp = "AFLM")
write_csv(coaches_votes, "data_pipeline/sample_coaches_votes.csv")

# 9. Fetch ScoreWorm Data and make plots (2025, Round 1 (OR), Hawks vs Sydney)
score_worm_data <- fetch_score_worm_data("CD_M20250140002")
write_csv(score_worm_data, "data_pipeline/sample_score_worm_data.csv")
score_worm_plot <- plot_score_worm("CD_M20250140002")
ggsave(
  filename = "data_pipeline/score_worm.png",
  plot = score_worm_plot,
  width = 10,
  height = 6,
  dpi = 300
)
score_worm_plot_totals <- plot_score_worm_totals("CD_M20250140002")
ggsave(
  filename = "data_pipeline/score_worm_totals.png",
  plot = score_worm_plot_totals,
  width = 10,
  height = 6,
  dpi = 300
)

# All of the below methods use footywire as the source, which now blocks non-browser requests via ModSecurity/Cloudflare, 
# preventing automated scraping with rvest/fitzRoy. These methods are commented out for now.
# I could maybe write a customer scraper myself if I decide I really need this data but for now I will ignore it.

# FootyWire now blocks non-browser requests via ModSecurity/Cloudflare, preventing automated scraping with rvest/fitzRoy?
# x. Fetch Out-of-Contract Players (2026)
# NOTE: fetch_out_of_contract_players_footywire also can be used
# cat("x. Fetching Out-of-Contract Players (2026)...\n")
# outofcontract_players <- fetch_outofcontract(2026)
# write_csv(outofcontract_players, "data_pipeline/sample_outofcontract_players.csv")

# FootyWire now blocks non-browser requests via ModSecurity/Cloudflare, preventing automated scraping with rvest/fitzRoy?
# x. Fetch All-Australian Squad and Team (2025)
# cat("x. Fetching All-Australian Squad and Team (2025)...\n")
# allaustralian_squad <- fetch_awards_allaustralian(2025, type = "squad")
# write_csv(allaustralian_squad, "data_pipeline/sample_allaustralian_squad.csv")
# allaustralian_team <- fetch_awards_allaustralian(2025, type = "team")
# write_csv(allaustralian_team, "data_pipeline/sample_allaustralian_team.csv")

# FootyWire now blocks non-browser requests via ModSecurity/Cloudflare, preventing automated scraping with rvest/fitzRoy?
#fetch_awards_brownlow()

# FootyWire now blocks non-browser requests via ModSecurity/Cloudflare, preventing automated scraping with rvest/fitzRoy?
#fetch_rising_star()

# FootyWire now blocks non-browser requests via ModSecurity/Cloudflare, preventing automated scraping with rvest/fitzRoy?
#fetch_betting_odds_footywire()

# FootyWire now blocks non-browser requests via ModSecurity/Cloudflare, preventing automated scraping with rvest/fitzRoy?
#fetch_fantasy_scores()

# FootyWire now blocks non-browser requests via ModSecurity/Cloudflare, preventing automated scraping with rvest/fitzRoy?
#fetch_supercoach_scores()

# FootyWire now blocks non-browser requests via ModSecurity/Cloudflare, preventing automated scraping with rvest/fitzRoy?
#fetch_scores()

# Still to check all below
#fetch_squiggle_data()

#get_afl_colour_palettes()

#plot_score_worm()

#plot_score_worm_totals()

#fetch_player_stats_fryzigg()

#TODO: Explore other functions at https://github.com/jimmyday12/fitzRoy/tree/main/R
#TODO: Explore Squiggle and Fryzigg later too!!

cat("Done! Check the data_pipeline folder for your CSV files.\n")