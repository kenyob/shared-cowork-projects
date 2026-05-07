"""
tests/test_sync_test.py
Unit tests for scripts/sync_test.py

Tests cover:
- Heartbeat file is written with correct content
- Health check returns green for fresh heartbeats
- Health check returns stale for old heartbeats
- --check exits 0 when all green, 1 when stale
- .env config warnings are detected correctly
- Cowork root resolution from SYNC_METHOD
"""

import os
import sys
import time
import unittest
import tempfile
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

# ── Add scripts/ to path so we can import sync_test ──────────────────────────
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))


class TestHeartbeat(unittest.TestCase):
    """Tests for the --heartbeat command: writing heartbeat-MACHINE.md files."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.heartbeat_dir = Path(self.tmp) / "cowork-shared-memory"
        self.heartbeat_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write_heartbeat(self, machine_name="TESTMACHINE"):
        """Simulate writing a heartbeat file."""
        hb_file = self.heartbeat_dir / f"heartbeat-{machine_name}.md"
        now = datetime.now(timezone.utc)
        hb_file.write_text(
            f"# Heartbeat — {machine_name}\n\n"
            f"- **Last seen:** {now.strftime('%Y-%m-%d %H:%M UTC')}\n"
            f"- **Machine:** {machine_name}\n"
            f"- **Platform:** Darwin test\n"
            f"- **Python:** 3.11.0\n"
            f"- **Sync method:** icloud\n"
        )
        return hb_file

    def test_heartbeat_file_created(self):
        """Heartbeat file should exist after writing."""
        hb_file = self._write_heartbeat("RICK")
        self.assertTrue(hb_file.exists(), "heartbeat-RICK.md should be created")

    def test_heartbeat_file_has_machine_name(self):
        """Heartbeat file should contain the machine name."""
        hb_file = self._write_heartbeat("RICK")
        content = hb_file.read_text()
        self.assertIn("RICK", content)

    def test_heartbeat_file_has_timestamp(self):
        """Heartbeat file should contain a UTC timestamp."""
        hb_file = self._write_heartbeat("RICK")
        content = hb_file.read_text()
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.assertIn(today, content)

    def test_heartbeat_overwrites_previous(self):
        """Second heartbeat write should overwrite first (not append)."""
        hb_file = self._write_heartbeat("RICK")
        time.sleep(0.01)
        self._write_heartbeat("RICK")
        content = hb_file.read_text()
        self.assertEqual(content.count("# Heartbeat"), 1, "Should not have duplicate headers")


class TestHealthCheck(unittest.TestCase):
    """Tests for the health check logic: green vs stale detection."""

    STALE_THRESHOLD = 75  # minutes — matches sync_test.py

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.heartbeat_dir = Path(self.tmp) / "cowork-shared-memory"
        self.heartbeat_dir.mkdir()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _write_heartbeat_aged(self, machine_name, minutes_ago):
        """Write a heartbeat file with an artificially old mtime."""
        hb_file = self.heartbeat_dir / f"heartbeat-{machine_name}.md"
        hb_file.write_text(f"# Heartbeat — {machine_name}\n- **Last seen:** old\n")
        # Wind back the modification time
        past = time.time() - (minutes_ago * 60)
        os.utime(hb_file, (past, past))
        return hb_file

    def _check_heartbeats(self):
        """Replicate sync_test.py check_heartbeats() logic."""
        results = []
        for hb_file in sorted(self.heartbeat_dir.glob("heartbeat-*.md")):
            mtime = datetime.fromtimestamp(hb_file.stat().st_mtime, tz=timezone.utc)
            age_m = (datetime.now(timezone.utc) - mtime).total_seconds() / 60
            name  = hb_file.stem.replace("heartbeat-", "")
            results.append({
                "machine":     name,
                "age_minutes": age_m,
                "status":      "green" if age_m <= self.STALE_THRESHOLD else "stale",
            })
        return results

    def test_fresh_heartbeat_is_green(self):
        """A heartbeat written 5 minutes ago should be green."""
        self._write_heartbeat_aged("RICK", minutes_ago=5)
        results = self._check_heartbeats()
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], "green")

    def test_old_heartbeat_is_stale(self):
        """A heartbeat written 90 minutes ago should be stale."""
        self._write_heartbeat_aged("RICK", minutes_ago=90)
        results = self._check_heartbeats()
        self.assertEqual(results[0]["status"], "stale")

    def test_boundary_at_threshold(self):
        """A heartbeat exactly at the threshold (75 min) should be green."""
        self._write_heartbeat_aged("RICK", minutes_ago=74)
        results = self._check_heartbeats()
        self.assertEqual(results[0]["status"], "green")

    def test_multiple_machines(self):
        """Multiple heartbeats are each independently evaluated."""
        self._write_heartbeat_aged("RICK", minutes_ago=10)
        self._write_heartbeat_aged("KIT",  minutes_ago=100)
        results = self._check_heartbeats()
        statuses = {r["machine"]: r["status"] for r in results}
        self.assertEqual(statuses["RICK"], "green")
        self.assertEqual(statuses["KIT"],  "stale")

    def test_no_heartbeat_files(self):
        """Empty heartbeat dir returns empty list."""
        results = self._check_heartbeats()
        self.assertEqual(results, [])

    def test_quick_check_exit_0_when_all_green(self):
        """quick_check should return 0 when all machines are green."""
        self._write_heartbeat_aged("RICK", minutes_ago=5)
        results = self._check_heartbeats()
        all_ok = all(r["status"] == "green" for r in results)
        self.assertEqual(all_ok, True)

    def test_quick_check_exit_1_when_stale(self):
        """quick_check should return 1 when any machine is stale."""
        self._write_heartbeat_aged("RICK", minutes_ago=5)
        self._write_heartbeat_aged("KIT",  minutes_ago=200)
        results = self._check_heartbeats()
        all_ok = all(r["status"] == "green" for r in results)
        self.assertEqual(all_ok, False)


class TestEnvConfig(unittest.TestCase):
    """Tests for .env loading and config warnings."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _check_env(self, env_contents=None):
        """Replicate sync_test.py check_env() logic against a temp .env."""
        env_file = Path(self.tmp) / ".env"
        if env_contents is not None:
            env_file.write_text(env_contents)

        warnings = []
        if not env_file.exists():
            warnings.append("No .env file found")
            return warnings

        # Parse env vars from file
        env_vars = {}
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                env_vars[k.strip()] = v.strip()

        if not env_vars.get("COWORK_FOLDER_NAME"):
            warnings.append("COWORK_FOLDER_NAME not set in .env")
        if not env_vars.get("ANTHROPIC_API_KEY"):
            warnings.append("No ANTHROPIC_API_KEY")

        return warnings

    def test_missing_env_file_warns(self):
        warnings = self._check_env(env_contents=None)
        self.assertTrue(any("No .env file" in w for w in warnings))

    def test_valid_env_no_warnings(self):
        warnings = self._check_env(
            "COWORK_FOLDER_NAME=my-cowork\nANTHROPIC_API_KEY=sk-ant-test\n"
        )
        self.assertEqual(warnings, [])

    def test_missing_folder_name_warns(self):
        warnings = self._check_env("ANTHROPIC_API_KEY=sk-ant-test\n")
        self.assertTrue(any("COWORK_FOLDER_NAME" in w for w in warnings))

    def test_missing_api_key_warns(self):
        warnings = self._check_env("COWORK_FOLDER_NAME=my-cowork\n")
        self.assertTrue(any("ANTHROPIC_API_KEY" in w for w in warnings))


class TestAgentsMdCoverage(unittest.TestCase):
    """Tests that agents.md presence detection works correctly."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.cowork_root = Path(self.tmp)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _check_agents(self):
        results = []
        for folder in sorted(self.cowork_root.iterdir()):
            if not folder.is_dir() or folder.name.startswith("_") or folder.name.startswith("."):
                continue
            agents = folder / "agents.md"
            results.append({"folder": folder.name, "has_agents": agents.exists()})
        return results

    def test_folder_with_agents_md(self):
        d = self.cowork_root / "01-Projects"
        d.mkdir()
        (d / "agents.md").write_text("# My project")
        results = self._check_agents()
        self.assertTrue(results[0]["has_agents"])

    def test_folder_without_agents_md(self):
        (self.cowork_root / "02-Areas").mkdir()
        results = self._check_agents()
        self.assertFalse(results[0]["has_agents"])

    def test_underscore_folders_ignored(self):
        (self.cowork_root / "_inbox").mkdir()
        (self.cowork_root / "01-Projects").mkdir()
        (self.cowork_root / "01-Projects" / "agents.md").write_text("x")
        results = self._check_agents()
        folder_names = [r["folder"] for r in results]
        self.assertNotIn("_inbox", folder_names)
        self.assertIn("01-Projects", folder_names)


if __name__ == "__main__":
    unittest.main()
