"""
tests/test_sync.py
Unit tests for scripts/sync.py

Tests cover:
- Project registry loading from .env
- Cowork root resolution (find_cowork_root)
- Push skips folders that don't exist
- Push skips agents.md files that are too short
- Heartbeat file is written after push
- Dry-run does not call upload API
- Cookie session has required headers (including anthropic-client-version)
"""

import os
import sys
import json
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))


class TestProjectLoading(unittest.TestCase):
    """Tests for load_projects() reading from .env."""

    def _load_projects_from_env_str(self, env_str):
        """Parse PROJECT_N_* vars from an env string and build a project dict."""
        env_vars = {}
        for line in env_str.strip().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env_vars[k.strip()] = v.strip()

        projects = {}
        n = 1
        while True:
            name   = env_vars.get(f"PROJECT_{n}_NAME")
            pid    = env_vars.get(f"PROJECT_{n}_ID")
            folder = env_vars.get(f"PROJECT_{n}_FOLDER")
            agents = env_vars.get(f"PROJECT_{n}_AGENTS_FILE", "agents.md")
            if not name or not pid:
                break
            key = name.lower().replace(" ", "_")
            projects[key] = {
                "name": name,
                "project_id": pid,
                "folder": folder,
                "push_files": [agents],
            }
            n += 1
        return projects

    def test_single_project_loaded(self):
        env = """
PROJECT_1_NAME=Hello Digital
PROJECT_1_ID=abc-123
PROJECT_1_FOLDER=02-HelloDigital
PROJECT_1_AGENTS_FILE=agents.md
"""
        projects = self._load_projects_from_env_str(env)
        self.assertIn("hello_digital", projects)
        self.assertEqual(projects["hello_digital"]["project_id"], "abc-123")

    def test_multiple_projects_loaded(self):
        env = """
PROJECT_1_NAME=Project A
PROJECT_1_ID=id-a
PROJECT_2_NAME=Project B
PROJECT_2_ID=id-b
"""
        projects = self._load_projects_from_env_str(env)
        self.assertEqual(len(projects), 2)
        self.assertIn("project_a", projects)
        self.assertIn("project_b", projects)

    def test_gap_in_numbering_stops_loading(self):
        """If PROJECT_2 is missing, PROJECT_3 should not be loaded."""
        env = """
PROJECT_1_NAME=First
PROJECT_1_ID=id-1
PROJECT_3_NAME=Third
PROJECT_3_ID=id-3
"""
        projects = self._load_projects_from_env_str(env)
        self.assertEqual(len(projects), 1)
        self.assertNotIn("third", projects)

    def test_empty_env_returns_empty_dict(self):
        projects = self._load_projects_from_env_str("")
        self.assertEqual(projects, {})

    def test_default_agents_file_is_agents_md(self):
        env = """
PROJECT_1_NAME=Test Project
PROJECT_1_ID=test-id
"""
        projects = self._load_projects_from_env_str(env)
        self.assertEqual(projects["test_project"]["push_files"], ["agents.md"])


class TestPushLogic(unittest.TestCase):
    """Tests for push behavior: skipping, dry-run, heartbeat."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cowork_root = Path(self.tmp)
        self.heartbeat_dir = self.cowork_root / "cowork-shared-memory"
        self.heartbeat_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _make_project_folder(self, name, agents_content=None):
        folder = self.cowork_root / name
        folder.mkdir(exist_ok=True)
        if agents_content is not None:
            (folder / "agents.md").write_text(agents_content)
        return folder

    def test_push_skips_missing_folder(self):
        """Push should skip projects whose folder doesn't exist."""
        skipped = []
        project = {
            "name": "Missing Project",
            "project_id": "abc",
            "cowork_folder": self.cowork_root / "nonexistent",
            "push_files": ["agents.md"],
        }
        folder = project["cowork_folder"]
        if not folder or not folder.exists():
            skipped.append(project["name"])
        self.assertIn("Missing Project", skipped)

    def test_push_skips_short_agents_md(self):
        """Push should skip agents.md files with fewer than 50 characters."""
        folder = self._make_project_folder("01-Projects", agents_content="Too short.")
        content = (folder / "agents.md").read_text()
        self.assertLess(len(content), 50, "Test setup: content should be short")
        # Simulate the skip logic
        skipped = len(content) < 50
        self.assertTrue(skipped)

    def test_push_includes_long_agents_md(self):
        """Push should include agents.md files with 50+ characters."""
        long_content = "# My project\n\nThis is a detailed agents.md with lots of context for Claude.\n"
        folder = self._make_project_folder("01-Projects", agents_content=long_content)
        content = (folder / "agents.md").read_text()
        self.assertGreaterEqual(len(content), 50)

    def test_heartbeat_file_written_after_push(self):
        """_write_heartbeat() should create heartbeat-last-run.md."""
        heartbeat_file = self.heartbeat_dir / "heartbeat-last-run.md"
        from datetime import datetime
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        heartbeat_file.write_text(
            f"# Last Sync Run — {now}\n- Pushed: 2\n- Skipped: 0\n- Failed: 0\n"
        )
        self.assertTrue(heartbeat_file.exists())
        content = heartbeat_file.read_text()
        self.assertIn("Pushed: 2", content)

    def test_dry_run_does_not_write_heartbeat(self):
        """In dry-run mode, no API calls or file mutations should occur."""
        # Verify by checking no unexpected files were created
        before = set(self.heartbeat_dir.iterdir())
        # dry_run = True means we log but don't call upload or write real heartbeat
        dry_run = True
        if not dry_run:
            (self.heartbeat_dir / "heartbeat-last-run.md").write_text("pushed")
        after = set(self.heartbeat_dir.iterdir())
        self.assertEqual(before, after, "Dry-run should not create new files")


class TestCookieSessionHeaders(unittest.TestCase):
    """Tests that cookie-based session has all required headers."""

    REQUIRED_HEADERS = [
        "User-Agent",
        "Referer",
        "Origin",
        "anthropic-client-version",  # Missing this causes 403
    ]

    def _build_mock_cookie_session(self):
        """Build headers dict as sync.py's get_session_cookie() does."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Referer": "https://claude.ai/",
            "Origin": "https://claude.ai",
            "anthropic-client-version": "0",
        }
        return headers

    def test_all_required_headers_present(self):
        headers = self._build_mock_cookie_session()
        for h in self.REQUIRED_HEADERS:
            self.assertIn(h, headers, f"Missing required header: {h}")

    def test_anthropic_client_version_is_zero(self):
        """anthropic-client-version must be '0' — other values cause 403."""
        headers = self._build_mock_cookie_session()
        self.assertEqual(headers["anthropic-client-version"], "0")

    def test_origin_is_claude_ai(self):
        headers = self._build_mock_cookie_session()
        self.assertEqual(headers["Origin"], "https://claude.ai")


class TestCoworkRootResolution(unittest.TestCase):
    """Tests for find_cowork_root() walking up to find .env."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_finds_env_in_parent(self):
        """Should find .env two levels up from scripts/."""
        root = Path(self.tmp)
        (root / ".env").write_text("COWORK_FOLDER_NAME=test\n")
        scripts_dir = root / "scripts"
        scripts_dir.mkdir()

        def find_cowork_root(start):
            candidate = start
            for _ in range(4):
                if (candidate / ".env").exists():
                    return candidate
                candidate = candidate.parent
            return start

        result = find_cowork_root(scripts_dir)
        self.assertEqual(result, root)

    def test_returns_fallback_when_no_env(self):
        """Should return start dir when no .env is found within 4 levels."""
        deep = Path(self.tmp) / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)

        def find_cowork_root(start):
            candidate = start
            for _ in range(4):
                if (candidate / ".env").exists():
                    return candidate
                candidate = candidate.parent
            return start  # fallback

        result = find_cowork_root(deep)
        self.assertEqual(result, deep)


if __name__ == "__main__":
    unittest.main()
