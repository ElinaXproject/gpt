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
        links = re.findall(r"\]\((docs/[^)#]+\.md)(?:#[^)]*)?\)", readme)
        self.assertTrue(links, "README should link to operational documents")
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


if __name__ == "__main__":
    unittest.main()
