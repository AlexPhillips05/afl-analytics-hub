# data_pipeline/db_connection.R
# Shared PostgreSQL connection for the R fetch scripts (source it from the repo root).
# Reads DATABASE_URL from data_pipeline/.env; an already-set DATABASE_URL takes precedence.

suppressPackageStartupMessages(library(DBI))

connect_db <- function() {
  if (Sys.getenv("DATABASE_URL") == "") readRenviron("data_pipeline/.env")
  url <- Sys.getenv("DATABASE_URL")
  if (url == "") stop("DATABASE_URL is not set: add it to data_pipeline/.env (see .env.example)")

  # RPostgres doesn't accept a URL, so split postgresql://user:password@host:port/dbname into parts.
  parts <- regmatches(url, regexec("^postgres(?:ql)?://([^:@/]+):([^@]*)@([^:/]+)(?::([0-9]+))?/([^?]+)", url, perl = TRUE))[[1]]
  if (length(parts) == 0) stop("DATABASE_URL must look like postgresql://user:password@host:port/dbname")
  dbConnect(
    RPostgres::Postgres(),
    user = URLdecode(parts[2]), password = URLdecode(parts[3]), host = parts[4],
    port = if (parts[5] == "") 5432L else as.integer(parts[5]), dbname = parts[6]
  )
}

# Replace every row of a Prisma-managed table, in one transaction. Never drops or recreates the table
# (dbWriteTable(overwrite = TRUE) would), so the schema stays owned by Prisma.
replace_table_rows <- function(con, table, rows) {
  invisible(dbWithTransaction(con, {
    dbExecute(con, paste("DELETE FROM", dbQuoteIdentifier(con, table)))
    dbAppendTable(con, table, rows)
  }))
}
