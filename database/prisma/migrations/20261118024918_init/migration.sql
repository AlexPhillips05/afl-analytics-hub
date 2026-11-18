-- CreateTable
CREATE TABLE "teams" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "state" TEXT NOT NULL,

    CONSTRAINT "teams_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "venues" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "state" TEXT NOT NULL,

    CONSTRAINT "venues_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "raw_afltables_results" (
    "game" INTEGER NOT NULL,
    "date" DATE NOT NULL,
    "season" INTEGER NOT NULL,
    "round" TEXT NOT NULL,
    "round_type" TEXT NOT NULL,
    "round_number" INTEGER,
    "home_team" TEXT NOT NULL,
    "home_goals" INTEGER NOT NULL,
    "home_behinds" INTEGER NOT NULL,
    "home_points" INTEGER NOT NULL,
    "away_team" TEXT NOT NULL,
    "away_goals" INTEGER NOT NULL,
    "away_behinds" INTEGER NOT NULL,
    "away_points" INTEGER NOT NULL,
    "venue" TEXT NOT NULL,
    "margin" INTEGER NOT NULL,
    "fetched_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "raw_afltables_results_pkey" PRIMARY KEY ("game")
);

-- CreateTable
CREATE TABLE "matches" (
    "id" TEXT NOT NULL,
    "afltables_game" INTEGER NOT NULL,
    "season" INTEGER NOT NULL,
    "round_number" INTEGER NOT NULL,
    "round_code" TEXT NOT NULL,
    "is_final" BOOLEAN NOT NULL,
    "date" DATE NOT NULL,
    "venue_id" INTEGER NOT NULL,
    "home_team_id" INTEGER NOT NULL,
    "away_team_id" INTEGER NOT NULL,
    "home_goals" INTEGER NOT NULL,
    "home_behinds" INTEGER NOT NULL,
    "away_goals" INTEGER NOT NULL,
    "away_behinds" INTEGER NOT NULL,

    CONSTRAINT "matches_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "elo_runs" (
    "id" SERIAL NOT NULL,
    "name" TEXT NOT NULL,
    "config" JSONB NOT NULL,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "elo_runs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "elo_ratings" (
    "run_id" INTEGER NOT NULL,
    "match_id" TEXT NOT NULL,
    "home_rating_pre" DOUBLE PRECISION NOT NULL,
    "away_rating_pre" DOUBLE PRECISION NOT NULL,
    "home_vai" DOUBLE PRECISION NOT NULL,
    "away_vai" DOUBLE PRECISION NOT NULL,
    "expected_home_win_prob" DOUBLE PRECISION NOT NULL,
    "league_avg_conversion" DOUBLE PRECISION NOT NULL,
    "adjusted_margin" DOUBLE PRECISION NOT NULL,
    "actual_home_outcome" DOUBLE PRECISION NOT NULL,
    "rating_change" DOUBLE PRECISION NOT NULL,
    "home_rating_post" DOUBLE PRECISION NOT NULL,
    "away_rating_post" DOUBLE PRECISION NOT NULL,

    CONSTRAINT "elo_ratings_pkey" PRIMARY KEY ("run_id","match_id")
);

-- CreateIndex
CREATE UNIQUE INDEX "teams_name_key" ON "teams"("name");

-- CreateIndex
CREATE UNIQUE INDEX "venues_name_key" ON "venues"("name");

-- CreateIndex
CREATE UNIQUE INDEX "matches_afltables_game_key" ON "matches"("afltables_game");

-- CreateIndex
CREATE INDEX "matches_season_round_number_idx" ON "matches"("season", "round_number");

-- CreateIndex
CREATE INDEX "matches_date_afltables_game_idx" ON "matches"("date", "afltables_game");

-- CreateIndex
CREATE UNIQUE INDEX "elo_runs_name_key" ON "elo_runs"("name");

-- AddForeignKey
ALTER TABLE "matches" ADD CONSTRAINT "matches_venue_id_fkey" FOREIGN KEY ("venue_id") REFERENCES "venues"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "matches" ADD CONSTRAINT "matches_home_team_id_fkey" FOREIGN KEY ("home_team_id") REFERENCES "teams"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "matches" ADD CONSTRAINT "matches_away_team_id_fkey" FOREIGN KEY ("away_team_id") REFERENCES "teams"("id") ON DELETE RESTRICT ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "elo_ratings" ADD CONSTRAINT "elo_ratings_run_id_fkey" FOREIGN KEY ("run_id") REFERENCES "elo_runs"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "elo_ratings" ADD CONSTRAINT "elo_ratings_match_id_fkey" FOREIGN KEY ("match_id") REFERENCES "matches"("id") ON DELETE CASCADE ON UPDATE CASCADE;
