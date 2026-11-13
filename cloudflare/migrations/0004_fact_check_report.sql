-- Persist the validated evidence report that unlocks factual content publication.
ALTER TABLE content_items ADD COLUMN fact_check_report_json TEXT NOT NULL DEFAULT '';
