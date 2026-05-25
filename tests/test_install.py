import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
_SAFE_SHELL_RE = re.compile(r"^[A-Za-z0-9_/:=.,+-]+$")


def _shell_quote(value):
    if _SAFE_SHELL_RE.match(value):
        return value
    return "'" + value.replace("'", "'\\''") + "'"


def _expected_cli(target):
    return "python3 " + _shell_quote(str(target / "scripts" / "pingcode.py"))


def _expected_ctx(target):
    return "python3 " + _shell_quote(str(target / "scripts" / "pingcode_ctx.py"))


def _run_install(args, env=None):
    return subprocess.run(
        ["node", "bin/install.js", *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def _isolated_home_env(home_dir, codex_home=None):
    env = os.environ.copy()
    env["HOME"] = str(home_dir)
    env.pop("PINGCODE_SKILL_NAME", None)
    if codex_home is None:
        env.pop("CODEX_HOME", None)
    else:
        env["CODEX_HOME"] = str(codex_home)
    return env


class InstallerSingleTargetTests(unittest.TestCase):
    def test_installed_docs_use_absolute_cli_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "pingcode skill"
            result = _run_install(["--target", str(target), "--force"])
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            skill_doc = (target / "SKILL.md").read_text(encoding="utf-8")
            readme = (target / "README.md").read_text(encoding="utf-8")
            workflows = (target / "references" / "workflows.md").read_text(encoding="utf-8")
            alias_doc = (target.parent / "pingcode-ctx" / "SKILL.md").read_text(encoding="utf-8")
            expected = _expected_cli(target)
            expected_ctx = _expected_ctx(target)
            ctx_bin_exists = (target / "bin" / "pingcode-ctx.js").exists()

        self.assertIn("Installed PingCode skill", result.stdout)
        self.assertIn(expected, skill_doc)
        self.assertIn(expected, readme)
        self.assertIn(expected, workflows)
        self.assertIn(expected_ctx, skill_doc)
        self.assertIn(expected_ctx, readme)
        self.assertIn(expected, alias_doc)
        self.assertIn(expected_ctx, alias_doc)
        self.assertTrue(ctx_bin_exists)
        self.assertNotIn("python3 scripts/pingcode.py", skill_doc)
        self.assertNotIn("python3 scripts/pingcode.py", readme)
        self.assertNotIn("python3 scripts/pingcode.py", workflows)
        self.assertNotIn("python3 scripts/pingcode_ctx.py", skill_doc)
        self.assertNotIn("python3 scripts/pingcode_ctx.py", readme)

    def test_target_combined_with_only_flag_errors(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "pingcode"
            result = _run_install(["--target", str(target), "--codex-only"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--target cannot be combined", result.stderr)


class InstallerMultiRootTests(unittest.TestCase):
    def _expected_paths(self, home, codex_home=None):
        codex_root = Path(codex_home) if codex_home else (home / ".codex")
        return {
            "codex": {
                "main": codex_root / "skills" / "pingcode",
                "alias": codex_root / "skills" / "pingcode-ctx",
            },
            "claude": {
                "main": home / ".claude" / "skills" / "pingcode",
                "alias": home / ".claude" / "skills" / "pingcode-ctx",
            },
            "openclaw": {
                "main": home / ".openclaw" / "skills" / "pingcode",
                "alias": home / ".openclaw" / "skills" / "pingcode-ctx",
            },
            "hermes": {
                "main": home / ".hermes" / "skills" / "project-management" / "pingcode",
                "alias": home / ".hermes" / "skills" / "project-management" / "pingcode-ctx",
            },
        }

    def _create_agent_homes(self, home, codex_home=None, keys=None):
        paths = self._expected_paths(home, codex_home=codex_home)
        selected = keys or paths.keys()
        for key in selected:
            if key == "hermes":
                (home / ".hermes").mkdir(parents=True, exist_ok=True)
            else:
                paths[key]["main"].parents[1].mkdir(parents=True, exist_ok=True)

    def _assert_installed(self, target):
        self.assertTrue((target / "SKILL.md").is_file(), f"SKILL.md missing in {target}")
        skill_doc = (target / "SKILL.md").read_text(encoding="utf-8")
        expected_cli = _expected_cli(target)
        expected_ctx = _expected_ctx(target)
        self.assertIn(expected_cli, skill_doc)
        self.assertIn(expected_ctx, skill_doc)
        self.assertNotIn("python3 scripts/pingcode.py", skill_doc)
        self.assertNotIn("python3 scripts/pingcode_ctx.py", skill_doc)

    def _assert_not_installed(self, target):
        self.assertFalse(target.exists(), f"unexpected install at {target}")

    def test_default_install_writes_existing_agent_roots(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            home.mkdir()
            env = _isolated_home_env(home)
            self._create_agent_homes(home)
            result = _run_install([], env=env)
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            paths = self._expected_paths(home)
            for key, entry in paths.items():
                self._assert_installed(entry["main"])
                self.assertTrue(entry["alias"].is_dir(), f"alias missing for {key}")
                alias_doc = (entry["alias"] / "SKILL.md").read_text(encoding="utf-8")
                expected_cli = _expected_cli(entry["main"])
                self.assertIn(expected_cli, alias_doc)
                self.assertIn("[ok]", result.stdout)

            for label in ("Codex", "Claude Code", "OpenClaw", "Hermes"):
                self.assertIn(label, result.stdout)

    def test_default_install_skips_missing_agent_roots(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            home.mkdir()
            env = _isolated_home_env(home)
            self._create_agent_homes(home, keys=("codex", "claude"))
            result = _run_install([], env=env)
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            paths = self._expected_paths(home)
            self._assert_installed(paths["codex"]["main"])
            self.assertTrue(paths["codex"]["alias"].is_dir())
            self._assert_installed(paths["claude"]["main"])
            self.assertTrue(paths["claude"]["alias"].is_dir())
            for key in ("openclaw", "hermes"):
                self._assert_not_installed(paths[key]["main"])
                self._assert_not_installed(paths[key]["alias"])

            self.assertIn("[skip] OpenClaw", result.stdout)
            self.assertIn("[skip] Hermes", result.stdout)

    def test_default_install_no_existing_agent_roots_is_noop(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            home.mkdir()
            env = _isolated_home_env(home)
            result = _run_install([], env=env)
            self.assertEqual(result.returncode, 0, msg=result.stderr)
            paths = self._expected_paths(home)
            for entry in paths.values():
                self._assert_not_installed(entry["main"])
                self._assert_not_installed(entry["alias"])
            self.assertIn("No supported agent directories were found", result.stdout)

    def test_codex_only_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            home.mkdir()
            env = _isolated_home_env(home)
            result = _run_install(["--codex-only"], env=env)
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            paths = self._expected_paths(home)
            self._assert_installed(paths["codex"]["main"])
            self.assertTrue(paths["codex"]["alias"].is_dir())
            for key in ("claude", "openclaw", "hermes"):
                self._assert_not_installed(paths[key]["main"])
                self._assert_not_installed(paths[key]["alias"])

    def test_claude_only_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            home.mkdir()
            env = _isolated_home_env(home)
            result = _run_install(["--claude-only"], env=env)
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            paths = self._expected_paths(home)
            self._assert_installed(paths["claude"]["main"])
            self.assertTrue(paths["claude"]["alias"].is_dir())
            for key in ("codex", "openclaw", "hermes"):
                self._assert_not_installed(paths[key]["main"])
                self._assert_not_installed(paths[key]["alias"])

    def test_openclaw_only_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            home.mkdir()
            env = _isolated_home_env(home)
            result = _run_install(["--openclaw-only"], env=env)
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            paths = self._expected_paths(home)
            self._assert_installed(paths["openclaw"]["main"])
            self.assertTrue(paths["openclaw"]["alias"].is_dir())
            for key in ("codex", "claude", "hermes"):
                self._assert_not_installed(paths[key]["main"])
                self._assert_not_installed(paths[key]["alias"])

    def test_hermes_only_scope(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            home.mkdir()
            env = _isolated_home_env(home)
            result = _run_install(["--hermes-only"], env=env)
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            paths = self._expected_paths(home)
            self._assert_installed(paths["hermes"]["main"])
            self.assertTrue(paths["hermes"]["alias"].is_dir())
            self.assertEqual(
                paths["hermes"]["main"].parent.name,
                "project-management",
                "Hermes install must live under the project-management category",
            )
            for key in ("codex", "claude", "openclaw"):
                self._assert_not_installed(paths[key]["main"])
                self._assert_not_installed(paths[key]["alias"])

    def test_codex_home_only_affects_codex_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            home.mkdir()
            codex_home = Path(tmpdir) / "custom-codex"
            env = _isolated_home_env(home, codex_home=codex_home)
            self._create_agent_homes(home, codex_home=codex_home)
            result = _run_install([], env=env)
            self.assertEqual(result.returncode, 0, msg=result.stderr)

            paths = self._expected_paths(home, codex_home=codex_home)
            self._assert_installed(paths["codex"]["main"])
            self.assertTrue(paths["codex"]["alias"].is_dir())
            # The default codex location MUST NOT be touched.
            default_codex = home / ".codex" / "skills" / "pingcode"
            self.assertFalse(default_codex.exists())
            # Other roots remain at their defaults under HOME.
            for key in ("claude", "openclaw", "hermes"):
                self._assert_installed(paths[key]["main"])

    @unittest.skipIf(sys.platform.startswith("win") or os.geteuid() == 0,
                     "permission-based isolation requires non-root POSIX env")
    def test_per_root_failure_does_not_abort_others(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            home = Path(tmpdir) / "home"
            home.mkdir()
            # Pre-create the claude skills root and make it unwritable so the
            # claude install fails while the others still run.
            claude_skills_root = home / ".claude" / "skills"
            claude_skills_root.mkdir(parents=True)
            self._create_agent_homes(home, keys=("codex", "openclaw", "hermes"))
            os.chmod(claude_skills_root, 0o500)
            env = _isolated_home_env(home)
            try:
                result = _run_install([], env=env)
            finally:
                # Restore permissions so TemporaryDirectory cleanup succeeds.
                os.chmod(claude_skills_root, 0o700)

            paths = self._expected_paths(home)
            # Claude root must have failed; the other three must have succeeded.
            self.assertFalse((paths["claude"]["main"] / "SKILL.md").exists())
            self._assert_installed(paths["codex"]["main"])
            self._assert_installed(paths["openclaw"]["main"])
            self._assert_installed(paths["hermes"]["main"])

            # Partial-success exits with code 2 so callers can detect it.
            self.assertEqual(result.returncode, 2, msg=result.stdout + result.stderr)
            self.assertIn("[fail]", result.stderr)
            self.assertIn("Claude Code", result.stderr)
            self.assertIn("[ok]", result.stdout)


if __name__ == "__main__":
    unittest.main()
