-- CreateTable
CREATE TABLE "raw_afltables_player_stats" (
    "id" SERIAL NOT NULL,
    "season" INTEGER NOT NULL,
    "round" TEXT NOT NULL,
    "date" DATE NOT NULL,
    "venue" TEXT NOT NULL,
    "home_team" TEXT NOT NULL,
    "away_team" TEXT NOT NULL,
    "playing_for" TEXT NOT NULL,
    "player_id" INTEGER,
    "first_name" TEXT NOT NULL,
    "surname" TEXT NOT NULL,
    "kicks" INTEGER,
    "marks" INTEGER,
    "handballs" INTEGER,
    "disposals" INTEGER,
    "goals" INTEGER,
    "behinds" INTEGER,
    "hit_outs" INTEGER,
    "tackles" INTEGER,
    "rebounds" INTEGER,
    "inside_50s" INTEGER,
    "clearances" INTEGER,
    "clangers" INTEGER,
    "frees_for" INTEGER,
    "frees_against" INTEGER,
    "brownlow_votes" INTEGER,
    "contested_possessions" INTEGER,
    "uncontested_possessions" INTEGER,
    "contested_marks" INTEGER,
    "marks_inside_50" INTEGER,
    "one_percenters" INTEGER,
    "bounces" INTEGER,
    "goal_assists" INTEGER,
    "time_on_ground" INTEGER,
    "substitute" TEXT,
    "fetched_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "raw_afltables_player_stats_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "team_match_stats" (
    "match_id" TEXT NOT NULL,
    "team_id" INTEGER NOT NULL,
    "is_home" BOOLEAN NOT NULL,
    "players" INTEGER NOT NULL,
    "kicks" INTEGER,
    "handballs" INTEGER,
    "marks" INTEGER,
    "tackles" INTEGER,
    "inside_50s" INTEGER,
    "rebounds" INTEGER,
    "clearances" INTEGER,
    "contested_possessions" INTEGER,
    "uncontested_possessions" INTEGER,
    "clangers" INTEGER,
    "frees_for" INTEGER,
    "frees_against" INTEGER,
    "hit_outs" INTEGER,
    "contested_marks" INTEGER,
    "marks_inside_50" INTEGER,
    "one_percenters" INTEGER,
    "goal_assists" INTEGER,
    "bounces" INTEGER,

    CONSTRAINT "team_match_stats_pkey" PRIMARY KEY ("match_id","team_id")
);

-- CreateIndex
CREATE INDEX "raw_afltables_player_stats_date_home_team_away_team_idx" ON "raw_afltables_player_stats"("date", "home_team", "away_team");

-- AddForeignKey
ALTER TABLE "team_match_stats" ADD CONSTRAINT "team_match_stats_match_id_fkey" FOREIGN KEY ("match_id") REFERENCES "matches"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "team_match_stats" ADD CONSTRAINT "team_match_stats_team_id_fkey" FOREIGN KEY ("team_id") REFERENCES "teams"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
