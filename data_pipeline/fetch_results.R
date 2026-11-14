# data_pipeline/fetch_results.R
# Fetch every AFL match result from 2000 to the current year from AFL Tables
# and write the raw rows to data_pipeline/data/afltables_results.csv (gitignored).
# No transformation here: elo/adapters.py owns the mapping into MatchResult.
#
# Run from the repo root:  Rscript data_pipeline/fetch_results.R

suppressPackageStartupMessages({
  library(fitzRoy)
  library(readr)
})

first_season <- 2000
last_season <- as.integer(format(Sys.Date(), "%Y"))
out_dir <- "data_pipeline/data"
out_file <- file.path(out_dir, "afltables_results.csv")

dir.create(out_dir, showWarnings = FALSE, recursive = TRUE)

cat(sprintf("Fetching AFL Tables results %d-%d...\n", first_season, last_season))
results <- fetch_results_afltables(first_season:last_season)
results <- results[results$Season >= first_season & results$Season <= last_season, ]

write_csv(results, out_file)
cat(sprintf("Wrote %d matches (%d seasons) to %s\n",
            nrow(results), length(unique(results$Season)), out_file))
