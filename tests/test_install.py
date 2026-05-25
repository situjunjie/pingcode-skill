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
            expected = f"python3 '{target / 'scripts' / 'pingcode.py'}'"

        self.assertIn("Installed PingCode skill", result.stdout)
        self.assertIn(expected, skill_doc)
        self.assertIn(expected, readme)
        self.assertIn(expected, workflows)
        self.assertNotIn("python3 scripts/pingcode.py", skill_doc)
        self.assertNotIn("python3 scripts/pingcode.py", readme)
        self.assertNotIn("python3 scripts/pingcode.py", workflows)


if __name__ == "__main__":
    unittest.main()
