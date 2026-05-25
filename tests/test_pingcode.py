import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import pingcode
from scripts import pingcode_ctx


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
    def parse_args_with_workspace_cache(self, items, cache_path):
        parser = pingcode.build_parser()
        return parser.parse_args(["--workspace-cache", str(cache_path), *items])

    def write_workspace_cache(
        self,
        cache_path,
        preferences=None,
        users=None,
        projects=None,
        sprints=None,
        work_item_types=None,
        states=None,
    ):
        payload = pingcode.empty_workspace_cache()
        payload["preferences"] = preferences or {}
        if users is not None:
            payload["users"] = {"values": users}
        if projects is not None:
            payload["projects"] = {"values": projects}
        if sprints is not None:
            payload["sprints"] = sprints
        if work_item_types is not None:
            payload["work_item_types"] = work_item_types
        if states is not None:
            payload["work_item_states"] = states
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(json.dumps(payload), encoding="utf-8")

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
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            self.write_workspace_cache(
                cache_path,
                preferences={
                    "current_user_id": "user-1",
                    "current_project_id": "project-1",
                    "current_sprint_id": "sprint-1",
                },
            )
            args = self.parse_args_with_workspace_cache(
                [
                    "--method",
                    "POST",
                    "--path",
                    "/v1/project/work_items",
                    "--data",
                    '{"project_id":"project-1","type_id":"story","title":"New story"}',
                    "--dry-run",
                ],
                cache_path,
            )

            with mock.patch.dict("os.environ", {}, clear=True):
                result = pingcode.run(args)

        self.assertTrue(result["dry_run"])
        self.assertEqual(result["method"], "POST")
        self.assertEqual(result["path"], "/v1/project/work_items")
        self.assertEqual(result["json"]["project_id"], "project-1")
        self.assertEqual(result["json"]["type_id"], "story")
        self.assertEqual(result["json"]["assignee_id"], "user-1")

    def test_workitem_create_defaults_assignee_from_cached_current_user(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            self.write_workspace_cache(
                cache_path,
                preferences={
                    "current_user_id": "user-cached",
                    "current_project_id": "project-1",
                    "current_sprint_id": "sprint-1",
                },
            )
            args = self.parse_args_with_workspace_cache(
                [
                    "--method",
                    "POST",
                    "--path",
                    "/v1/project/work_items",
                    "--data",
                    '{"project_id":"project-1","type_id":"story","title":"New story"}',
                    "--dry-run",
                ],
                cache_path,
            )

            with mock.patch.dict("os.environ", {}, clear=True):
                result = pingcode.run(args)

        self.assertEqual(result["json"]["assignee_id"], "user-cached")

    def test_workitem_create_all_users_skips_default_assignee(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            self.write_workspace_cache(
                cache_path,
                preferences={
                    "current_user_id": "user-cached",
                    "current_project_id": "project-1",
                    "current_sprint_id": "sprint-1",
                },
            )
            args = self.parse_args_with_workspace_cache(
                [
                    "--method",
                    "POST",
                    "--path",
                    "/v1/project/work_items",
                    "--all-users",
                    "--data",
                    '{"project_id":"project-1","type_id":"story","title":"New story"}',
                    "--dry-run",
                ],
                cache_path,
            )

            with mock.patch.dict("os.environ", {"PINGCODE_USER_ID": "user-1"}):
                result = pingcode.run(args)

        self.assertNotIn("assignee_id", result["json"])

    def test_workitem_create_missing_current_user_prints_identity_guidance(self):
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
                "--no-workspace-cache",
            ]
        )

        with mock.patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(pingcode.PingCodeError) as ctx:
                pingcode.run(args)

        self.assertIn("PingCode workspace context is incomplete", str(ctx.exception))
        self.assertIn("current_user_id", str(ctx.exception))
        self.assertIn("pingcode_ctx.py", str(ctx.exception))

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
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            self.write_workspace_cache(
                cache_path,
                preferences={
                    "current_user_id": "user-cached",
                    "current_project_id": "project-1",
                    "current_sprint_id": "sprint-1",
                },
            )
            args = self.parse_args_with_workspace_cache(
                [
                    "--method",
                    "GET",
                    "--path",
                    "/v1/project/work_items",
                    "--param",
                    "assignee_ids=@me",
                    "--dry-run",
                ],
                cache_path,
            )

            with mock.patch.dict("os.environ", {"PINGCODE_USER_ID": "user-1"}):
                result = pingcode.run(args)

        self.assertEqual(result["params"]["assignee_ids"], "user-1")
        self.assertEqual(result["params"]["project_ids"], "project-1")
        self.assertEqual(result["params"]["sprint_ids"], "sprint-1")

    def test_me_placeholder_expands_from_user_id_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            self.write_workspace_cache(
                cache_path,
                preferences={
                    "current_user_id": "user-cached",
                    "current_project_id": "project-1",
                    "current_sprint_id": "sprint-1",
                },
            )
            args = self.parse_args_with_workspace_cache(
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
                ],
                cache_path,
            )

            with mock.patch.dict("os.environ", {}, clear=True):
                result = pingcode.run(args)

        self.assertEqual(result["json"]["assignee_id"], "user-flag-1")

    def test_me_name_placeholder_expands_from_user_name_flag(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            self.write_workspace_cache(
                cache_path,
                preferences={
                    "current_user_id": "user-1",
                    "current_project_id": "project-1",
                    "current_sprint_id": "sprint-1",
                },
            )
            args = self.parse_args_with_workspace_cache(
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
                ],
                cache_path,
            )

            with mock.patch.dict("os.environ", {}, clear=True):
                result = pingcode.run(args)

        self.assertEqual(result["params"]["keywords"], "Situ")
        self.assertEqual(result["params"]["assignee_ids"], "user-1")

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
                "--no-workspace-cache",
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

    def test_workspace_current_user_falls_back_to_cached_preference(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            self.write_workspace_cache(
                cache_path,
                preferences={
                    "current_user_id": "user-cached",
                    "current_project_id": "project-cached",
                    "current_sprint_id": "sprint-cached",
                },
            )
            args = self.parse_args_with_workspace_cache(
                [
                    "--method",
                    "GET",
                    "--path",
                    "/v1/project/work_items",
                    "--dry-run",
                ],
                cache_path,
            )

            with mock.patch.dict("os.environ", {}, clear=True):
                result = pingcode.run(args)

        self.assertEqual(result["params"]["assignee_ids"], "user-cached")
        self.assertEqual(result["params"]["project_ids"], "project-cached")
        self.assertEqual(result["params"]["sprint_ids"], "sprint-cached")

    def test_all_project_and_sprint_flags_skip_default_filters(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            self.write_workspace_cache(cache_path, preferences={"current_user_id": "user-cached"})
            args = self.parse_args_with_workspace_cache(
                [
                    "--method",
                    "GET",
                    "--path",
                    "/v1/project/work_items",
                    "--all-projects",
                    "--all-sprints",
                    "--dry-run",
                ],
                cache_path,
            )

            result = pingcode.run(args)

        self.assertEqual(result["params"], {"assignee_ids": "user-cached"})

    def test_missing_current_project_returns_ctx_guidance_without_fetch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            self.write_workspace_cache(cache_path, preferences={"current_user_id": "user-cached"})
            args = self.parse_args_with_workspace_cache(
                [
                    "--method",
                    "GET",
                    "--path",
                    "/v1/project/work_items",
                    "--token",
                    "token-1",
                ],
                cache_path,
            )

            with mock.patch("urllib.request.urlopen") as urlopen:
                with self.assertRaises(pingcode.PingCodeError) as ctx:
                    pingcode.run(args)

        urlopen.assert_not_called()
        self.assertIn("PingCode workspace context is incomplete", str(ctx.exception))
        self.assertIn("pingcode_ctx.py", str(ctx.exception))

    def test_missing_current_project_dry_run_does_not_fetch_projects(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            self.write_workspace_cache(cache_path, preferences={"current_user_id": "user-cached"})
            args = self.parse_args_with_workspace_cache(
                [
                    "--method",
                    "GET",
                    "--path",
                    "/v1/project/work_items",
                    "--dry-run",
                ],
                cache_path,
            )

            with mock.patch("urllib.request.urlopen") as urlopen:
                with self.assertRaises(pingcode.PingCodeError) as ctx:
                    pingcode.run(args)

        urlopen.assert_not_called()
        self.assertIn("PingCode workspace context is incomplete", str(ctx.exception))

    def test_missing_current_sprint_returns_ctx_guidance_without_fetch(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            self.write_workspace_cache(
                cache_path,
                preferences={"current_user_id": "user-cached", "current_project_id": "project-1"},
            )
            args = self.parse_args_with_workspace_cache(
                [
                    "--method",
                    "GET",
                    "--path",
                    "/v1/project/work_items",
                    "--token",
                    "token-1",
                ],
                cache_path,
            )

            with mock.patch("urllib.request.urlopen") as urlopen:
                with self.assertRaises(pingcode.PingCodeError) as ctx:
                    pingcode.run(args)

        urlopen.assert_not_called()
        self.assertIn("PingCode workspace context is incomplete", str(ctx.exception))
        self.assertIn("pingcode_ctx.py", str(ctx.exception))

    def test_user_name_placeholder_expands_from_cached_users(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            self.write_workspace_cache(
                cache_path,
                preferences={
                    "current_user_id": "user-cached",
                    "current_project_id": "project-1",
                    "current_sprint_id": "sprint-1",
                },
                users=[{"id": "user-2", "name": "Alice Chen", "email": "alice@example.test"}],
            )
            args = self.parse_args_with_workspace_cache(
                [
                    "--method",
                    "GET",
                    "--path",
                    "/v1/project/work_items",
                    "--param",
                    "assignee_ids=@user:Alice",
                    "--dry-run",
                ],
                cache_path,
            )

            result = pingcode.run(args)

        self.assertEqual(result["params"]["assignee_ids"], "user-2")

    def test_cache_states_reuses_workspace_cache_without_network(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            cached_states = {"values": [{"id": "state-1", "name": "进行中"}]}
            self.write_workspace_cache(
                cache_path,
                states={"project-1::task": cached_states},
            )
            args = self.parse_args_with_workspace_cache(
                [
                    "--method",
                    "GET",
                    "--path",
                    "/v1/project/work_item/states",
                    "--param",
                    "project_id=project-1",
                    "--param",
                    "work_item_type_id=task",
                ],
                cache_path,
            )

            with mock.patch("urllib.request.urlopen") as urlopen:
                result = pingcode.run(args)

        self.assertEqual(result, cached_states)
        urlopen.assert_not_called()

    def test_work_item_types_write_and_reuse_workspace_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            args = self.parse_args_with_workspace_cache(
                [
                    "--method",
                    "GET",
                    "--path",
                    "/v1/project/work_item/types",
                    "--token",
                    "token-1",
                    "--param",
                    "project_id=project-1",
                ],
                cache_path,
            )

            with mock.patch(
                "urllib.request.urlopen",
                return_value=FakeResponse({"values": [{"id": "story", "name": "故事"}]}),
            ) as urlopen:
                result = pingcode.run(args)

            payload = json.loads(cache_path.read_text(encoding="utf-8"))

            with mock.patch("urllib.request.urlopen") as cached_urlopen:
                cached_result = pingcode.run(args)

        self.assertEqual(result["values"][0]["id"], "story")
        self.assertEqual(payload["work_item_types"]["project-1"]["values"][0]["name"], "故事")
        self.assertEqual(cached_result["values"][0]["id"], "story")
        self.assertEqual(urlopen.call_count, 1)
        cached_urlopen.assert_not_called()

    def test_get_states_writes_workspace_cache_after_network_success(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            args = self.parse_args_with_workspace_cache(
                [
                    "--method",
                    "GET",
                    "--path",
                    "/v1/project/work_item/states",
                    "--token",
                    "token-1",
                    "--param",
                    "project_id=project-1",
                    "--param",
                    "work_item_type_id=task",
                ],
                cache_path,
            )

            with mock.patch(
                "urllib.request.urlopen",
                return_value=FakeResponse({"values": [{"id": "state-1", "name": "已完成"}]}),
            ):
                result = pingcode.run(args)

            payload = json.loads(cache_path.read_text(encoding="utf-8"))

        self.assertEqual(result["values"][0]["id"], "state-1")
        self.assertEqual(payload["work_item_states"]["project-1::task"]["values"][0]["name"], "已完成")

    def test_cache_states_refresh_bypasses_stale_workspace_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            self.write_workspace_cache(
                cache_path,
                preferences={"current_project_id": "project-1"},
                states={"project-1::task": {"values": [{"id": "old-state", "name": "旧状态"}]}},
            )
            args = self.parse_args_with_workspace_cache(
                [
                    "--cache-states",
                    "--work-item-type-id",
                    "task",
                    "--token",
                    "token-1",
                ],
                cache_path,
            )

            with mock.patch(
                "urllib.request.urlopen",
                return_value=FakeResponse({"values": [{"id": "new-state", "name": "新状态"}]}),
            ) as urlopen:
                result = pingcode.run(args)

            payload = json.loads(cache_path.read_text(encoding="utf-8"))

        self.assertEqual(result["values"][0]["id"], "new-state")
        self.assertEqual(payload["work_item_states"]["project-1::task"]["values"][0]["id"], "new-state")
        urlopen.assert_called_once()

    def test_cache_states_without_type_refreshes_types_and_all_states(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            self.write_workspace_cache(cache_path, preferences={"current_project_id": "project-1"})
            args = self.parse_args_with_workspace_cache(
                [
                    "--cache-states",
                    "--token",
                    "token-1",
                ],
                cache_path,
            )

            with mock.patch(
                "urllib.request.urlopen",
                side_effect=[
                    FakeResponse({"values": [{"id": "story", "name": "故事"}, {"id": "task", "name": "任务"}]}),
                    FakeResponse({"values": [{"id": "story-done", "name": "已完成"}]}),
                    FakeResponse({"values": [{"id": "task-done", "name": "已完成"}]}),
                ],
            ) as urlopen:
                result = pingcode.run(args)

            payload = json.loads(cache_path.read_text(encoding="utf-8"))

        self.assertEqual(result["project_id"], "project-1")
        self.assertEqual(set(result["work_item_states"].keys()), {"story", "task"})
        self.assertEqual(payload["work_item_types"]["project-1"]["values"][0]["id"], "story")
        self.assertEqual(payload["work_item_states"]["project-1::story"]["values"][0]["id"], "story-done")
        self.assertEqual(payload["work_item_states"]["project-1::task"]["values"][0]["id"], "task-done")
        self.assertEqual(urlopen.call_count, 3)

    def test_cache_users_uses_project_members_when_project_id_is_available(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            args = self.parse_args_with_workspace_cache(
                [
                    "--cache-users",
                    "--project-id",
                    "project-1",
                    "--token",
                    "token-1",
                ],
                cache_path,
            )

            with mock.patch(
                "urllib.request.urlopen",
                return_value=FakeResponse({"values": [{"id": "user-1", "name": "Situ"}]}),
            ) as urlopen:
                result = pingcode.run(args)

            request = urlopen.call_args.args[0]
            payload = json.loads(cache_path.read_text(encoding="utf-8"))

        self.assertIn("/v1/project/projects/project-1/members", request.full_url)
        self.assertEqual(result["values"][0]["id"], "user-1")
        self.assertEqual(payload["users"]["project_id"], "project-1")

    def test_set_current_user_accepts_cached_user_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            self.write_workspace_cache(
                cache_path,
                users=[{"id": "user-1", "name": "Situ", "email": "situ@example.test"}],
            )
            args = self.parse_args_with_workspace_cache(["--set-current-user", "Situ"], cache_path)

            result = pingcode.run(args)

            payload = json.loads(cache_path.read_text(encoding="utf-8"))

        self.assertEqual(result["preferences"]["current_user_id"], "user-1")
        self.assertEqual(payload["preferences"]["current_user_name"], "Situ")

    def test_set_current_user_accepts_cached_project_member_display_name(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            self.write_workspace_cache(
                cache_path,
                users=[
                    {
                        "id": "member-1",
                        "type": "user",
                        "user": {
                            "id": "user-1",
                            "display_name": "司徒",
                            "name": "situjunjie",
                            "email": "situ@example.test",
                        },
                    }
                ],
            )
            args = self.parse_args_with_workspace_cache(["--set-current-user", "司徒"], cache_path)

            result = pingcode.run(args)

            payload = json.loads(cache_path.read_text(encoding="utf-8"))

        self.assertEqual(result["preferences"]["current_user_id"], "user-1")
        self.assertEqual(result["preferences"]["current_user_name"], "司徒")
        self.assertEqual(payload["preferences"]["current_user_id"], "user-1")

    def test_context_options_user_outputs_nested_project_member_names(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            args = self.parse_args_with_workspace_cache(
                [
                    "--context-options",
                    "user",
                    "--project-id",
                    "project-1",
                    "--token",
                    "token-1",
                ],
                cache_path,
            )

            with mock.patch(
                "urllib.request.urlopen",
                return_value=FakeResponse(
                    {
                        "values": [
                            {
                                "id": "member-1",
                                "project": {"id": "project-1", "name": "Core Project"},
                                "user": {
                                    "id": "user-1",
                                    "display_name": "司徒",
                                    "name": "situjunjie",
                                    "email": "situ@example.test",
                                },
                            }
                        ]
                    }
                ),
            ):
                result = pingcode.run(args)

        self.assertEqual(result["kind"], "user")
        self.assertEqual(result["total"], 1)
        self.assertEqual(result["options"][0]["id"], "user-1")
        self.assertEqual(result["options"][0]["display_name"], "司徒")
        self.assertEqual(result["options"][0]["name"], "situjunjie")
        self.assertEqual(result["options"][0]["email"], "situ@example.test")

    def test_pingcode_ctx_selects_and_caches_workspace_context(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_path = Path(tmpdir) / "workspace.json"
            args = pingcode_ctx.build_parser().parse_args(
                [
                    "--workspace-cache",
                    str(cache_path),
                    "--token",
                    "token-1",
                ]
            )
            responses = [
                {"values": [{"id": "project-1", "name": "Core Project"}]},
                {"values": [{"id": "sprint-1", "name": "Sprint 1"}]},
                {
                    "values": [
                        {
                            "id": "member-1",
                            "user": {
                                "id": "user-1",
                                "display_name": "司徒",
                                "name": "situjunjie",
                                "email": "situ@example.test",
                            },
                        }
                    ]
                },
            ]

            output = io.StringIO()
            with mock.patch("urllib.request.urlopen", side_effect=[FakeResponse(item) for item in responses]):
                selections = iter(["1", "1", "1"])
                with mock.patch("sys.stdout", output):
                    result = pingcode_ctx.run(args, input_func=lambda _prompt: next(selections))

            payload = json.loads(cache_path.read_text(encoding="utf-8"))

        self.assertEqual(result["preferences"]["current_project_id"], "project-1")
        self.assertEqual(result["preferences"]["current_sprint_id"], "sprint-1")
        self.assertEqual(result["preferences"]["current_user_id"], "user-1")
        self.assertEqual(payload["preferences"]["current_project_name"], "Core Project")
        self.assertEqual(payload["preferences"]["current_sprint_name"], "Sprint 1")
        self.assertEqual(payload["preferences"]["current_user_name"], "司徒")
        self.assertIn("司徒", output.getvalue())
        self.assertIn("situjunjie", output.getvalue())

    def test_main_prints_help(self):
        parser = pingcode.build_parser()
        output = io.StringIO()
        with self.assertRaises(SystemExit) as ctx, mock.patch("sys.stdout", output):
            parser.parse_args(["--help"])

        self.assertEqual(ctx.exception.code, 0)
        self.assertIn("Single-command PingCode REST API caller", output.getvalue())


if __name__ == "__main__":
    unittest.main()
