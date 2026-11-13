-- Persist an auditable human safety-review decision for every publishable content item.
ALTER TABLE content_items ADD COLUMN safety_review_reference TEXT NOT NULL DEFAULT '';
ALTER TABLE content_items ADD COLUMN safety_review_report_json TEXT NOT NULL DEFAULT '';
