from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class WorkbenchRepositoryTests(unittest.TestCase):
    def read(self, relative_path: str) -> str:
        path = ROOT / relative_path
        self.assertTrue(path.is_file(), f"Missing required file: {relative_path}")
        return path.read_text(encoding="utf-8")

    def test_required_operational_documents_exist(self):
        required = (
            "README.md",
            "docs/OPERATING_PROTOCOL.md",
            "docs/QUALITY_CHECKLIST.md",
            "docs/EVAL_CASES.md",
            "docs/INTEGRATION_STATUS.md",
            "docs/WORKBENCH_STATE.md",
        )
        for path in required:
            with self.subTest(path=path):
                self.read(path)

    def test_autored_project_documents_and_runtime_files_exist(self):
        required = (
            "docs/AUTORED_IDEA_ARCHITECTURE_PL.md",
            "docs/AUTORED_IDEA_EXECUTION_PLAN_PL.md",
            "docs/AUTORED_IDEA_SECURITY_DR_PL.md",
            "docs/AUTORED_IDEA_TEST_PLAN_PL.md",
            "docs/AUTORED_IDEA_AUDIT_2026-11-13_PL.md",
            "docs/AUTORED_IDEA_STATE_PL.md",
            "docs/AUTORED_IDEA_DECISIONS_PL.md",
            "docs/AUTORED_IDEA_DEPLOYMENT_2026-11-13_PL.md",
            "docs/AUTORED_IDEA_RENDERER_PL.md",
            "autored/README.md",
            "autored/core.py",
            "cloudflare/worker.js",
            "cloudflare/migrations/0001_initial.sql",
            "scripts/render_vertical_video.py",
            "scripts/smoke_input.json",
            "requirements-render.txt",
            ".github/workflows/render-smoke.yml",
            "wrangler.toml",
        )
        for path in required:
            with self.subTest(path=path):
                self.read(path)

    def test_autored_architecture_maps_all_target_profiles(self):
        content = self.read("docs/AUTORED_IDEA_ARCHITECTURE_PL.md")
        for profile in ("@ocenionona6", "@pieknemedia", "@MemoryAgent-r3"):
            with self.subTest(profile=profile):
                self.assertIn(profile, content)

    def test_autored_test_matrix_has_22_cases(self):
        content = self.read("docs/AUTORED_IDEA_TEST_PLAN_PL.md")
        case_ids = set(re.findall(r"^\|\s*(T\d{2})\s*\|", content, re.MULTILINE))
        self.assertEqual({f"T{i:02d}" for i in range(1, 24)}, case_ids)
        self.assertIn("NOT RUN", content)

    def test_autored_security_plan_includes_backup_and_restore(self):
        content = self.read("docs/AUTORED_IDEA_SECURITY_DR_PL.md")
        for required in ("Backup & Disaster Recovery", "SHA-256", "RPO", "RTO", "test odtworzenia"):
            with self.subTest(required=required):
                self.assertIn(required, content)

    def test_autored_execution_plan_has_staged_gates(self):
        content = self.read("docs/AUTORED_IDEA_EXECUTION_PLAN_PL.md")
        for stage in range(0, 13):
            with self.subTest(stage=stage):
                self.assertRegex(content, rf"(?m)^\|\s*{stage}\s*\|")
        self.assertIn("BLOCKED", content)

    def test_all_documented_regression_cases_are_present(self):
        content = self.read("docs/EVAL_CASES.md")
        case_ids = set(re.findall(r"^\|\s*(E\d{2})\s*\|", content, re.MULTILINE))
        self.assertEqual({f"E{i:02d}" for i in range(1, 11)}, case_ids)
        for status in ("PASS", "FAIL", "NOT RUN"):
            self.assertIn(status, content)

    def test_operating_protocol_defines_all_statuses(self):
        content = self.read("docs/OPERATING_PROTOCOL.md")
        for status in ("PLAN", "DOING", "DONE", "VERIFIED", "BLOCKED"):
            with self.subTest(status=status):
                self.assertIn(status, content)

    def test_readme_internal_markdown_links_resolve(self):
        readme = self.read("README.md")
        links = re.findall(r"\]\(([^)#]+\.md)(?:#[^)]*)?\)", readme)
        self.assertTrue(links, "README should link to Markdown documents")
        for link in links:
            with self.subTest(link=link):
                self.assertTrue((ROOT / link).is_file(), f"Broken internal link: {link}")

    def test_reusable_templates_exist(self):
        required = (
            "templates/DECISIONS_TEMPLATE.md",
            "templates/ERRORS_TEMPLATE.md",
            "templates/PROJECT_TEMPLATE.md",
            "templates/STATE_TEMPLATE.md",
            "templates/TASKS_TEMPLATE.md",
        )
        for path in required:
            with self.subTest(path=path):
                self.assertTrue(self.read(path).strip())

    def test_markdown_files_do_not_contain_common_live_secret_formats(self):
        patterns = (
            re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
            re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}\b"),
            re.compile(r"\bsk-[A-Za-z0-9]{32,}\b"),
            re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
            re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        )
        markdown_files = list(ROOT.rglob("*.md"))
        self.assertTrue(markdown_files, "No Markdown files found")
        for path in markdown_files:
            content = path.read_text(encoding="utf-8")
            for pattern in patterns:
                with self.subTest(path=str(path), pattern=pattern.pattern):
                    self.assertIsNone(pattern.search(content), f"Possible secret found in {path}")

    def test_ci_workflow_uses_read_only_permissions_and_pinned_actions(self):
        content = self.read(".github/workflows/quality.yml")
        self.assertIn("permissions:\n  contents: read", content)
        self.assertNotIn("write-all", content)
        action_refs = re.findall(r"^\s*uses:\s*([^#\s]+)", content, re.MULTILINE)
        self.assertTrue(action_refs, "CI workflow should use explicit actions")
        for reference in action_refs:
            with self.subTest(action=reference):
                self.assertRegex(reference, r"@[0-9a-f]{40}$")

    def test_dependabot_checks_github_actions_weekly(self):
        content = self.read(".github/dependabot.yml")
        self.assertIn("package-ecosystem: github-actions", content)
        self.assertIn("interval: weekly", content)
        self.assertIn("open-pull-requests-limit: 5", content)

    def test_cloudflare_worker_has_guarded_json_and_idempotent_daily_jobs(self):
        worker = self.read("cloudflare/worker.js")
        required = (
            'response_format: { type: "json_object" }',
            "result?.choices?.[0]?.message?.content",
            "new Intl.DateTimeFormat",
            'timeZone: TIME_ZONE',
            "INSERT OR IGNORE INTO content_items",
            "daily_run_date",
            "run_still_active",
            'url.pathname === "/health"',
            "ctx.waitUntil(runDaily",
        )
        for value in required:
            with self.subTest(value=value):
                self.assertIn(value, worker)

    def test_cloudflare_worker_does_not_publish_before_platform_adapters_exist(self):
        worker = self.read("cloudflare/worker.js")
        self.assertIn("stage: \"idea_only\"", worker)
        self.assertNotIn("video.publish", worker)
        self.assertNotIn("youtube.upload", worker)

    def test_d1_schema_contains_all_required_entities_and_profiles(self):
        schema = self.read("cloudflare/migrations/0001_initial.sql")
        for table in ("profiles", "content_items", "publication_jobs", "quota_ledger", "daily_runs", "events"):
            with self.subTest(table=table):
                self.assertIn(f"CREATE TABLE IF NOT EXISTS {table}", schema)
        for profile in ("@ocenionona6", "@pieknemedia", "@MemoryAgent-r3"):
            with self.subTest(profile=profile):
                self.assertIn(profile, schema)
        self.assertIn("idx_content_daily_profile", schema)

    def test_wranger_config_matches_deployed_database_and_timezone_schedule(self):
        config = self.read("wrangler.toml")
        self.assertIn('name = "autored-idea-api"', config)
        self.assertIn('database_name = "autored_idea_db"', config)
        self.assertIn('binding = "AI"', config)
        self.assertIn('crons = ["0 7,8 * * *"]', config)

    def test_renderer_uses_commercially_cleared_polish_voice(self):
        renderer = self.read("scripts/render_vertical_video.py")
        self.assertIn('VOICE = "pl_PL-darkman-medium"', renderer)
        self.assertIn("from PIL import Image, ImageDraw, ImageFont", renderer)
        self.assertIn("make_text_overlay", renderer)
        self.assertIn("write_background", renderer)
        for theme in ("tech", "humor", "education"):
            self.assertIn(f"\"{theme}\"", renderer)
        self.assertIn("music_license_reference_required", renderer)
        self.assertIn("licensed_music_required", renderer)
        self.assertIn('"libx264"', renderer)
        self.assertIn('"aac"', renderer)
        self.assertIn('"48000"', renderer)


if __name__ == "__main__":
    unittest.main()
