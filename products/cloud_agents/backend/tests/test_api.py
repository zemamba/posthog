from typing import Any

from posthog.test.base import APIBaseTest
from unittest.mock import patch

from parameterized import parameterized
from rest_framework import status

from posthog.models import Organization, Team
from posthog.models.scoping import team_scope

from products.cloud_agents.backend.models import CloudAgentProfile, TeamCloudAgentsConfig
from products.cloud_agents.backend.tests.base import CloudAgentsFlagMixin, TasksFakeMixin

# name, method, path below cloud_agents/, is a write, body
ROUTES: list[tuple[str, str, str, bool, dict[str, Any] | None]] = [
    ("profiles_list", "get", "profiles/", False, None),
    ("profiles_create", "post", "profiles/", True, {"name": "New profile"}),
    ("profiles_retrieve", "get", "profiles/{profile}/", False, None),
    ("profiles_update", "patch", "profiles/{profile}/", True, {"description": "Changed"}),
    ("profiles_delete", "delete", "profiles/{profile}/", True, None),
    ("settings_retrieve", "get", "settings/", False, None),
    ("settings_update", "patch", "settings/", True, {"branch": "main"}),
    ("runs_list", "get", "runs/", False, None),
    ("runs_create", "post", "runs/", True, {"prompt": "Fix it", "repository": "acme/app"}),
    ("runs_retrieve", "get", "runs/{run}/", False, None),
    ("runs_messages", "post", "runs/{run}/messages/", True, {"content": "Also fix the lint"}),
    ("runs_cancel", "post", "runs/{run}/cancel/", True, None),
    ("runs_usage", "get", "runs/{run}/usage/", False, None),
    ("runs_events", "get", "runs/{run}/events/", False, None),
    ("catalog", "get", "catalog/", False, None),
    ("estimate", "get", "estimate/?size=4x16&minutes=15", False, None),
    ("usage", "get", "usage/", False, None),
]
DETAIL_ROUTES = [route for route in ROUTES if "{" in route[2]]
WRITE_ROUTES = [route for route in ROUTES if route[3]]
READ_ROUTES = [route for route in ROUTES if not route[3]]


class CloudAgentsAPITestCase(TasksFakeMixin, CloudAgentsFlagMixin, APIBaseTest):
    def setUp(self) -> None:
        super().setUp()
        with team_scope(self.team.id):
            self.profile = CloudAgentProfile.objects.create(team=self.team, name="Backend", created_by=self.user)
        self.run_row = self.make_run(task_status="in_progress")

    def call(self, method: str, path: str, body: dict[str, Any] | None = None, **extra: Any) -> Any:
        url = f"{self.base_url()}/{path}".format(profile=self.profile.id, run=self.run_row.id)
        return getattr(self.client, method)(url, data=body, format="json", **extra)


class TestAccess(CloudAgentsAPITestCase):
    @parameterized.expand(ROUTES)
    def test_flag_off_blocks_every_route(self, _name: str, method: str, path: str, _write: bool, body: Any) -> None:
        self.set_cloud_agents_flag(False)
        assert self.call(method, path, body).status_code == status.HTTP_403_FORBIDDEN

    @parameterized.expand(WRITE_ROUTES)
    def test_read_scope_cannot_write(self, _name: str, method: str, path: str, _write: bool, body: Any) -> None:
        key = self.create_personal_api_key_with_scopes(["cloud_agent:read"])
        self.client.logout()
        response = self.call(method, path, body, HTTP_AUTHORIZATION=f"Bearer {key}")
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.json()

    @parameterized.expand(READ_ROUTES)
    def test_read_scope_can_read(self, _name: str, method: str, path: str, _write: bool, body: Any) -> None:
        key = self.create_personal_api_key_with_scopes(["cloud_agent:read"])
        self.client.logout()
        response = self.call(method, path, body, HTTP_AUTHORIZATION=f"Bearer {key}")
        assert response.status_code == status.HTTP_200_OK, response.json()

    @parameterized.expand(WRITE_ROUTES)
    def test_write_scope_can_write(self, _name: str, method: str, path: str, _write: bool, body: Any) -> None:
        key = self.create_personal_api_key_with_scopes(["cloud_agent:write"])
        self.client.logout()
        response = self.call(method, path, body, HTTP_AUTHORIZATION=f"Bearer {key}")
        assert 200 <= response.status_code < 300, response.content

    @parameterized.expand(ROUTES)
    def test_other_scope_is_refused(self, _name: str, method: str, path: str, _write: bool, body: Any) -> None:
        key = self.create_personal_api_key_with_scopes(["insight:write"])
        self.client.logout()
        response = self.call(method, path, body, HTTP_AUTHORIZATION=f"Bearer {key}")
        assert response.status_code == status.HTTP_403_FORBIDDEN, response.json()

    def test_flag_check_that_raises_blocks_the_route(self) -> None:
        with patch("posthoganalytics.feature_enabled", side_effect=RuntimeError("down")):
            assert self.call("get", "runs/").status_code == status.HTTP_403_FORBIDDEN

    @parameterized.expand(
        [
            ("run_create", "post", "runs/", {"prompt": "Fix it", "repository": "acme/app"}),
            ("profile_create", "post", "profiles/", {"name": "New profile"}),
            ("profile_update", "patch", "profiles/{profile}/", {}),
            ("settings_update", "patch", "settings/", {}),
        ]
    )
    def test_own_key_inference_is_not_accepted(self, _name: str, method: str, path: str, body: dict[str, Any]) -> None:
        response = self.call(method, path, {**body, "inference": "own_key"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST, response.content
        assert response.json()["attr"] == "inference"
        assert self.tasks.create_calls == []
        assert CloudAgentProfile.objects.count() == 1
        assert self.call("get", "profiles/{profile}/").json()["inference"] is None
        assert self.call("get", "settings/").json()["inference"] is None

    @parameterized.expand(DETAIL_ROUTES)
    def test_other_team_rows_are_not_found(self, _name: str, method: str, path: str, _write: bool, body: Any) -> None:
        other_org = Organization.objects.create(name="Other")
        other_team = Team.objects.create(organization=other_org, name="Other team")
        with team_scope(other_team.id):
            self.profile = CloudAgentProfile.objects.create(team=other_team, name="Theirs")
        self.run_row = self.make_run(team=other_team, task_status="in_progress")

        assert self.call(method, path, body).status_code == status.HTTP_404_NOT_FOUND
        with team_scope(other_team.id):
            assert CloudAgentProfile.objects.get(id=self.profile.id).deleted is False
        self.mocks["runs.signal_task_run_user_message"].assert_not_called()
        self.mocks["runs.cancel_task_run"].assert_not_called()

    @parameterized.expand(
        [
            ("profiles", "profiles/", [{"name": "Zeta"}, {"name": "alpha"}]),
        ]
    )
    def test_list_pages_do_not_repeat_or_skip_rows(self, _name: str, path: str, bodies: list[dict[str, Any]]) -> None:
        for body in bodies:
            assert self.call("post", path, body).status_code == status.HTTP_201_CREATED
        everything = self.call("get", path).json()
        assert everything["count"] == 3

        paged_ids: list[str] = []
        for offset in range(0, 4, 2):
            page = self.call("get", f"{path}?limit=2&offset={offset}").json()
            assert page["count"] == 3
            paged_ids.extend(row["id"] for row in page["results"])
        assert paged_ids == [row["id"] for row in everything["results"]]

    @parameterized.expand([("profiles/not-a-uuid/",), ("runs/not-a-uuid/",)])
    def test_malformed_id_is_not_found(self, path: str) -> None:
        assert self.call("get", path).status_code == status.HTTP_404_NOT_FOUND


class TestProfiles(CloudAgentsAPITestCase):
    def test_create_and_retrieve(self) -> None:
        body = {
            "name": "Frontend",
            "description": "UI work",
            "repository": "acme/web",
            "size": "8x16",
            "inference": "own_subscription",
            "create_pr": False,
            "tags": ["ui"],
        }
        created = self.call("post", "profiles/", body)
        assert created.status_code == status.HTTP_201_CREATED, created.json()
        fetched = self.call("get", f"profiles/{created.json()['id']}/").json()
        assert {key: fetched[key] for key in body} == body
        assert fetched["created_by"] == self.user.id
        assert fetched["branch"] is None

    def test_list_hides_deleted_profiles(self) -> None:
        self.call("post", "profiles/", {"name": "Alpha"})
        assert self.call("delete", "profiles/{profile}/").status_code == status.HTTP_204_NO_CONTENT
        names = [profile["name"] for profile in self.call("get", "profiles/").json()["results"]]
        assert names == ["Alpha"]
        assert self.call("get", "profiles/{profile}/").status_code == status.HTTP_404_NOT_FOUND

    @parameterized.expand([("same_case", "Backend"), ("other_case", "bACKEND"), ("padded", "  backend  ")])
    def test_name_is_unique_without_regard_to_case(self, _name: str, name: str) -> None:
        response = self.call("post", "profiles/", {"name": name})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["attr"] == "name"

    def test_rename_to_taken_name_is_rejected_and_own_name_is_allowed(self) -> None:
        other = self.call("post", "profiles/", {"name": "Other"}).json()
        assert self.call("patch", f"profiles/{other['id']}/", {"name": "BACKEND"}).status_code == 400
        assert self.call("patch", "profiles/{profile}/", {"name": "backend"}).status_code == 200

    def test_delete_frees_the_name(self) -> None:
        self.call("delete", "profiles/{profile}/")
        assert self.call("post", "profiles/", {"name": "backend"}).status_code == status.HTTP_201_CREATED

    def test_partial_update_changes_only_sent_fields_and_null_clears(self) -> None:
        self.call("patch", "profiles/{profile}/", {"repository": "acme/api", "branch": "develop"})
        response = self.call("patch", "profiles/{profile}/", {"branch": None})
        assert response.status_code == status.HTTP_200_OK, response.json()
        assert (response.json()["repository"], response.json()["branch"]) == ("acme/api", None)

    @parameterized.expand(
        [
            ("duration_low", {"max_duration_minutes": 4}, "max_duration_minutes"),
            ("duration_high", {"max_duration_minutes": 241}, "max_duration_minutes"),
            ("size", {"size": "3x3"}, "size"),
            ("repository", {"repository": "not a repo"}, "repository"),
            ("cost", {"max_cost_usd": "0"}, "max_cost_usd"),
            ("reserved_pr_mode", {"pr_mode": "ready"}, "pr_mode"),
            ("reserved_duration", {"max_duration_minutes": 30}, "max_duration_minutes"),
            ("reserved_cost", {"max_cost_usd": "12.50"}, "max_cost_usd"),
            ("blank_name", {"name": " "}, "name"),
        ]
    )
    def test_invalid_values_are_rejected(self, _name: str, body: dict[str, Any], attr: str) -> None:
        response = self.call("patch", "profiles/{profile}/", body)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["attr"] == attr


class TestSettings(CloudAgentsAPITestCase):
    def test_first_read_creates_the_row_with_default_limits(self) -> None:
        assert not TeamCloudAgentsConfig.objects.filter(team_id=self.team.id).exists()
        body = self.call("get", "settings/").json()
        assert TeamCloudAgentsConfig.objects.filter(team_id=self.team.id).count() == 1
        assert body["repository"] is None
        assert body["default_profile"] is None
        assert (body["max_concurrent_runs"], body["create_rate_per_hour"]) == (5, 60)

    def test_patch_updates_and_clears(self) -> None:
        body = {"repository": "acme/app", "size": "2x4", "default_profile": str(self.profile.id)}
        updated = self.call("patch", "settings/", body)
        assert updated.status_code == status.HTTP_200_OK, updated.json()
        assert {key: updated.json()[key] for key in body} == body

        cleared = self.call("patch", "settings/", {"default_profile": None}).json()
        assert cleared["default_profile"] is None
        assert cleared["repository"] == "acme/app"

    def test_limits_are_read_only(self) -> None:
        self.call("patch", "settings/", {"max_concurrent_runs": 500, "create_rate_per_hour": 5000})
        body = self.call("get", "settings/").json()
        assert (body["max_concurrent_runs"], body["create_rate_per_hour"]) == (5, 60)

    @parameterized.expand([("other_team",), ("deleted",)])
    def test_default_profile_must_be_an_active_profile_of_the_team(self, case: str) -> None:
        if case == "other_team":
            other_team = Team.objects.create(organization=self.organization, name="Other team")
            with team_scope(other_team.id):
                profile = CloudAgentProfile.objects.create(team=other_team, name="Theirs")
        else:
            profile = CloudAgentProfile.objects.create(team=self.team, name="Gone", deleted=True)
        response = self.call("patch", "settings/", {"default_profile": str(profile.id)})
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["attr"] == "default_profile"

    def test_deleting_the_default_profile_clears_it(self) -> None:
        self.call("patch", "settings/", {"default_profile": str(self.profile.id)})
        self.call("delete", "profiles/{profile}/")
        assert self.call("get", "settings/").json()["default_profile"] is None
