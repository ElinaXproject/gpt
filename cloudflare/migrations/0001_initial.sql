-- AUTORED IDEA D1 baseline schema
-- Applied to autored_idea_db (EU jurisdiction, EEUR primary) on 2026-11-13.
-- This is the canonical schema snapshot; never apply blindly to an existing database.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS profiles (
  id TEXT PRIMARY KEY,
  platform TEXT NOT NULL CHECK (platform IN ('tiktok','youtube')),
  handle TEXT NOT NULL UNIQUE,
  timezone TEXT NOT NULL DEFAULT 'Europe/Warsaw',
  enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0,1)),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS content_items (
  id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL REFERENCES profiles(id),
  topic TEXT NOT NULL,
  title TEXT NOT NULL DEFAULT '',
  description TEXT NOT NULL DEFAULT '',
  hashtags_json TEXT NOT NULL DEFAULT '[]',
  script TEXT NOT NULL DEFAULT '',
  source_urls_json TEXT NOT NULL DEFAULT '[]',
  rights_reference TEXT NOT NULL DEFAULT '',
  ai_disclosure_required INTEGER NOT NULL DEFAULT 0,
  ai_disclosure_set INTEGER NOT NULL DEFAULT 0,
  media_mime TEXT NOT NULL DEFAULT '',
  media_bytes INTEGER NOT NULL DEFAULT 0,
  media_sha256 TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'idea' CHECK (status IN ('idea','draft','ready','blocked','scheduled','published','failed')),
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  daily_run_date TEXT,
  safety_review_status TEXT NOT NULL DEFAULT 'pending' CHECK (safety_review_status IN ('pending','passed','blocked'))
);

CREATE TABLE IF NOT EXISTS publication_jobs (
  id TEXT PRIMARY KEY,
  content_id TEXT NOT NULL REFERENCES content_items(id),
  profile_id TEXT NOT NULL REFERENCES profiles(id),
  scheduled_at TEXT NOT NULL,
  idempotency_key TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'planned' CHECK (status IN ('planned','ready','publishing','published','retry_wait','blocked','failed')),
  attempts INTEGER NOT NULL DEFAULT 0,
  platform_post_id TEXT,
  published_url TEXT,
  last_error_code TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS quota_ledger (
  id TEXT PRIMARY KEY,
  profile_id TEXT NOT NULL REFERENCES profiles(id),
  period TEXT NOT NULL,
  provider TEXT NOT NULL,
  quota_limit INTEGER NOT NULL,
  used INTEGER NOT NULL DEFAULT 0,
  checked_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(profile_id, period, provider)
);

CREATE TABLE IF NOT EXISTS daily_runs (
  local_date TEXT PRIMARY KEY,
  status TEXT NOT NULL CHECK (status IN ('running','succeeded','failed','skipped')),
  started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  completed_at TEXT,
  result_count INTEGER NOT NULL DEFAULT 0,
  error_code TEXT
);

CREATE TABLE IF NOT EXISTS events (
  id TEXT PRIMARY KEY,
  event_type TEXT NOT NULL,
  profile_id TEXT,
  content_id TEXT,
  job_id TEXT,
  detail_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_content_profile_status ON content_items(profile_id, status, created_at);
CREATE UNIQUE INDEX IF NOT EXISTS idx_content_daily_profile ON content_items(profile_id, daily_run_date) WHERE daily_run_date IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_jobs_status_schedule ON publication_jobs(status, scheduled_at);
CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);

INSERT OR IGNORE INTO profiles (id, platform, handle) VALUES
  ('tiktok_ocenionona6','tiktok','@ocenionona6'),
  ('tiktok_pieknemedia','tiktok','@pieknemedia'),
  ('youtube_memoryagent','youtube','@MemoryAgent-r3c');
