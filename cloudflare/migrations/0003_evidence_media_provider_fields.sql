-- Auditable evidence and licensed-media metadata for publication gates.
ALTER TABLE content_items ADD COLUMN source_published_at_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE content_items ADD COLUMN fact_check_reference TEXT NOT NULL DEFAULT '';
ALTER TABLE content_items ADD COLUMN fact_check_passed INTEGER NOT NULL DEFAULT 0 CHECK (fact_check_passed IN (0,1));
ALTER TABLE content_items ADD COLUMN music_license_reference TEXT NOT NULL DEFAULT '';
ALTER TABLE content_items ADD COLUMN music_embedded INTEGER NOT NULL DEFAULT 0 CHECK (music_embedded IN (0,1));

ALTER TABLE publication_jobs ADD COLUMN provider TEXT NOT NULL DEFAULT 'publora';
ALTER TABLE publication_jobs ADD COLUMN media_artifact_id TEXT;
