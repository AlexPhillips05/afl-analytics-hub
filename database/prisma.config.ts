// Prisma configuration for afl-analytics-hub's database.
// The connection URLs live in ONE gitignored file shared with R and Python: ../data_pipeline/.env
// PRISMA_TARGET=test points Prisma at TEST_DATABASE_URL instead (used by `npm run migrate:deploy:test`).
import path from "node:path";
import { config } from "dotenv";
import { defineConfig, env } from "prisma/config";

config({ path: path.join(__dirname, "..", "data_pipeline", ".env"), quiet: true });

export default defineConfig({
  schema: "prisma/schema.prisma",
  migrations: { path: "prisma/migrations" },
  datasource: {
    url: process.env.PRISMA_TARGET === "test" ? env("TEST_DATABASE_URL") : env("DATABASE_URL"),
  },
});
