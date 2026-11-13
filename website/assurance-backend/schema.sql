-- Cloudflare D1 database: mathgraph_assurance_leads
-- Account-side binding is named LEADS; these records are never published by the website.
CREATE TABLE IF NOT EXISTS submissions (
  id TEXT PRIMARY KEY NOT NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  repository_url TEXT NOT NULL,
  claim TEXT NOT NULL,
  decision TEXT NOT NULL,
  consequence TEXT NOT NULL,
  evidence TEXT NOT NULL,
  relationship TEXT NOT NULL,
  email TEXT NOT NULL,
  campaign_source TEXT NOT NULL DEFAULT '',
  campaign_medium TEXT NOT NULL DEFAULT '',
  campaign_name TEXT NOT NULL DEFAULT '',
  status TEXT NOT NULL DEFAULT 'NEW'
    CHECK (status IN ('NEW','SELECTED','DECLINED','IN_REVIEW','FINDING_DELIVERED','CLOSED')),
  consent_version TEXT NOT NULL DEFAULT 'mathgraph-assurance-v1'
);
CREATE INDEX IF NOT EXISTS submissions_status_date ON submissions(status,created_at);
