import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import pingcode


class FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return self.payload


class PingCodeCliTests(unittest.TestCase):
    def test_build_url_merges_query_parameters(self):
        url = pingcode.build_url(
            "https://open.pingcode.com",
            "/v1/project/work_items?identifier=SCR-1",
            {"page_size": 20, "project_ids": ["p1", "p2"]},
        )

        self.assertEqual(
            url,
            "https://open.pingcode.com/v1/project/work_items?identifier=SCR-1&page_size=20&project_ids=p1%2Cp2",
        )

    def test_single_command_workitem_create_dry_run_payload(self):
        parser = pingcode.build_parser()
        args = parser.parse_args(
            [
                "--method",
                "POST",
                "--path",
                "/v1/project/work_items",
                "--data",
                '{"project_id":"project-1","type_id":"story","title":"New story"}',
                "--dry-run",
            ]
        )

        result = pingcode.run(args)

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["method"], "POST")
        self.assertEqual(result["path"], "/v1/project/work_items")
        self.assertEqual(result["json"]["project_id"], "project-1")
        self.assertEqual(result["json"]["type_id"], "story")

    def test_single_command_maps_params(self):
        parser = pingcode.build_parser()
        args = parser.parse_args(
            [
                "--method",
                "GET",
                "--path",
                "/v1/project/work_item/states",
                "--param",
                "project_id=project-1",
                "--param",
                "work_item_type_id=story",
                "--dry-run",
            ]
        )

        result = pingcode.run(args)

        self.assertEqual(result["path"], "/v1/project/work_item/states")
        self.assertEqual(result["params"]["project_id"], "project-1")
        self.assertEqual(result["params"]["work_item_type_id"], "story")

    def test_me_placeholder_expands_from_environment(self):
        parser = pingcode.build_parser()
        args = parser.parse_args(
            [
                "--method",
                "GET",
                "--path",
                "/v1/project/work_items",
                "--param",
                "assignee_ids=@me",
                "--dry-run",
            ]
        )

        with mock.patch.dict("os.environ", {"PINGCODE_USER_ID": "user-1"}):
            result = pingcode.run(args)

        self.assertEqual(result["params"]["assignee_ids"], "user-1")

    def test_me_placeholder_expands_from_user_id_flag(self):
        parser = pingcode.build_parser()
        args = parser.parse_args(
            [
                "--method",
                "POST",
                "--path",
                "/v1/project/work_items",
                "--user-id",
                "user-flag-1",
                "--data",
                '{"project_id":"project-1","type_id":"task","title":"Task","assignee_id":"@me"}',
                "--dry-run",
            ]
        )

        with mock.patch.dict("os.environ", {}, clear=True):
            result = pingcode.run(args)

        self.assertEqual(result["json"]["assignee_id"], "user-flag-1")

    def test_me_name_placeholder_expands_from_user_name_flag(self):
        parser = pingcode.build_parser()
        args = parser.parse_args(
            [
                "--method",
                "GET",
                "--path",
                "/v1/project/work_items",
                "--user-name",
                "Situ",
                "--param",
                "keywords=@me_name",
                "--dry-run",
            ]
        )

        with mock.patch.dict("os.environ", {}, clear=True):
            result = pingcode.run(args)

        self.assertEqual(result["params"]["keywords"], "Situ")

    def test_missing_me_placeholder_prints_identity_guidance(self):
        parser = pingcode.build_parser()
        args = parser.parse_args(
            [
                "--method",
                "GET",
                "--path",
                "/v1/project/work_items",
                "--param",
                "assignee_ids=@me",
                "--dry-run",
            ]
        )

        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(pingcode.PingCodeError) as ctx:
                pingcode.run(args)

        self.assertIn("PINGCODE_USER_ID", str(ctx.exception))
        self.assertIn("--user-id", str(ctx.exception))
        self.assertIn("client_credentials is an enterprise token", str(ctx.exception))

    def test_missing_credentials_prints_environment_guidance(self):
        client = pingcode.PingCodeClient(
            base_url="https://open.pingcode.com",
            client_id=None,
            client_secret=None,
            token_cache=None,
        )

        with self.assertRaises(pingcode.PingCodeError) as ctx:
            client.access_token()

        self.assertIn("PINGCODE_CLIENT_ID", str(ctx.exception))
        self.assertIn("export PINGCODE_CLIENT_SECRET", str(ctx.exception))

    def test_access_token_uses_client_credentials_and_writes_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "token.json"
            client = pingcode.PingCodeClient(
                base_url="https://open.pingcode.com",
                client_id="client",
                client_secret="secret",
                token_cache=str(cache_path),
            )

            with mock.patch(
                "urllib.request.urlopen",
                return_value=FakeResponse({"access_token": "token-1", "expires_in": 3600}),
            ) as urlopen:
                token = client.access_token()

            self.assertEqual(token, "token-1")
            self.assertTrue(cache_path.exists())
            request = urlopen.call_args.args[0]
            self.assertIn("grant_type=client_credentials", request.full_url)
            self.assertIn("client_id=client", request.full_url)
            self.assertIn("client_secret=secret", request.full_url)

    def test_main_prints_help(self):
        parser = pingcode.build_parser()
        output = io.StringIO()
        with self.assertRaises(SystemExit) as ctx, mock.patch("sys.stdout", output):
            parser.parse_args(["--help"])

        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("Single-command PingCode REST API caller", output.getvalue())


if __name__ == "__main__":
    unittest.main()
