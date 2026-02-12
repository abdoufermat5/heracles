-- Heracles PostgreSQL Initialization Script
-- ==========================================
-- Extensions only — all tables are managed by Alembic migrations.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
