import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class InstallerTests(unittest.TestCase):
    def test_installed_docs_use_absolute_cli_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "pingcode skill"
            result = subprocess.run(
                ["node", "bin/install.js", "--target", str(target), "--force"],
                cwd=REPO_ROOT,
                text=True,
                capture_output=True,
                check=True,
            )

            skill_doc = (target / "SKILL.md").read_text(encoding="utf-8")
            readme = (target / "README.md").read_text(encoding="utf-8")
            workflows = (target / "references" / "workflows.md").read_text(encoding="utf-8")
            alias_doc = (target.parent / "pingcode-ctx" / "SKILL.md").read_text(encoding="utf-8")
            expected = f"python3 '{target / 'scripts' / 'pingcode.py'}'"
            expected_ctx = f"python3 '{target / 'scripts' / 'pingcode_ctx.py'}'"
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


if __name__ == "__main__":
    unittest.main()
