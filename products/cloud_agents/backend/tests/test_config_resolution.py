import dataclasses
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from django.test import SimpleTestCase

from parameterized import parameterized

from products.cloud_agents.backend.facade.contracts import (
    InvalidInput,
    ProfileDTO,
    RepositoryRequired,
    ResolvedRunConfig,
    RunCreateInput,
    TeamSettingsDTO,
)
from products.cloud_agents.backend.facade.enums import InferenceMode, PrMode, SizeName, size_shape
from products.cloud_agents.backend.logic.config_resolution import render_prompt, resolve_run_config

PROFILE_ID = UUID("01900000-0000-7000-8000-000000000001")
NOW = datetime(2026, 1, 1, tzinfo=UTC)

EMPTY_TEAM = TeamSettingsDTO(
    repository=None,
    branch=None,
    model=None,
    size=None,
    inference=None,
    instructions=None,
    create_pr=None,
    pr_mode=None,
    max_duration_minutes=None,
    max_cost_usd=None,
    default_profile_id=None,
    max_concurrent_runs=5,
    create_rate_per_hour=60,
    webhook_secret_set=False,
    updated_at=None,
)
EMPTY_PROFILE = ProfileDTO(
    id=PROFILE_ID,
    name="default",
    description="",
    repository=None,
    branch=None,
    model=None,
    size=None,
    inference=None,
    instructions=None,
    create_pr=None,
    pr_mode=None,
    max_duration_minutes=None,
    max_cost_usd=None,
    tags=[],
    webhook_url=None,
    created_by_id=None,
    created_at=NOW,
    updated_at=NOW,
)

# field, call value, profile value, team value, product default
PRECEDENCE_FIELDS: list[tuple[str, Any, Any, Any, Any]] = [
    ("branch", "call-branch", "profile-branch", "team-branch", None),
    ("model", "call-model", "profile-model", "team-model", None),
    ("size", SizeName.S_1X2, SizeName.S_2X4, SizeName.S_8X32, SizeName.S_4X16),
    ("inference", InferenceMode.OWN_KEY, InferenceMode.OWN_SUBSCRIPTION, InferenceMode.POSTHOG, InferenceMode.AUTO),
    # Adjacent levels differ, so a level cannot pass on the value of the level below it.
    ("create_pr", False, True, False, True),
    ("pr_mode", PrMode.READY, PrMode.DRAFT, PrMode.READY, PrMode.DRAFT),
    ("max_duration_minutes", 10, 20, 30, 60),
    ("max_cost_usd", Decimal("1.00"), Decimal("2.00"), Decimal("3.00"), None),
]


def _resolve(call: dict[str, Any], profile: dict[str, Any] | None, team: dict[str, Any]) -> ResolvedRunConfig:
    return resolve_run_config(
        RunCreateInput(prompt="Fix the bug", **call),
        dataclasses.replace(EMPTY_PROFILE, **profile) if profile is not None else None,
        dataclasses.replace(EMPTY_TEAM, **team),
    )


class TestResolveRunConfig(SimpleTestCase):
    @parameterized.expand([(field, *values) for field, *values in PRECEDENCE_FIELDS])
    def test_field_precedence(self, field: str, call: Any, profile: Any, team: Any, default: Any) -> None:
        base = {"repository": "acme/app"}

        assert getattr(_resolve({**base, field: call}, {field: profile}, {field: team}), field) == call
        assert getattr(_resolve(base, {field: profile}, {field: team}), field) == profile
        assert getattr(_resolve(base, {}, {field: team}), field) == team
        assert getattr(_resolve(base, None, {field: team}), field) == team
        assert getattr(_resolve(base, {}, {}), field) == default

    @parameterized.expand(
        [
            (
                "call",
                {"repository": "call/repo"},
                {"repository": "profile/repo"},
                {"repository": "team/repo"},
                "call/repo",
            ),
            ("profile", {}, {"repository": "profile/repo"}, {"repository": "team/repo"}, "profile/repo"),
            ("team", {}, {}, {"repository": "team/repo"}, "team/repo"),
            ("team_without_profile", {}, None, {"repository": "team/repo"}, "team/repo"),
        ]
    )
    def test_repository_precedence(
        self, _name: str, call: dict, profile: dict | None, team: dict, expected: str
    ) -> None:
        assert _resolve(call, profile, team).repository == expected

    @parameterized.expand([("no_profile", None), ("empty_profile", {}), ("blank_values", {"repository": ""})])
    def test_missing_repository_is_rejected(self, _name: str, profile: dict | None) -> None:
        with self.assertRaises(RepositoryRequired):
            _resolve({}, profile, {})

    @parameterized.expand(
        [
            ("union_keeps_first_position", ["a", "b"], ["b", "c"], ["a", "b", "c"]),
            ("profile_only", ["a"], None, ["a"]),
            ("call_only", [], ["z", "a"], ["z", "a"]),
            ("none", [], None, []),
        ]
    )
    def test_tags_union_is_order_stable(
        self, _name: str, profile_tags: list[str], call_tags: list[str] | None, expected: list[str]
    ) -> None:
        config = _resolve({"repository": "acme/app", "tags": call_tags}, {"tags": profile_tags}, {})
        assert config.tags == expected

    @parameterized.expand(
        [
            ("all_levels", "call", "profile", "team", "team\n\nprofile\n\ncall"),
            ("skips_missing_levels", "call", None, "team", "team\n\ncall"),
            ("skips_blank_levels", "call", "  ", None, "call"),
            ("none", None, None, None, None),
        ]
    )
    def test_instructions_join_team_then_profile_then_call(
        self, _name: str, call: str | None, profile: str | None, team: str | None, expected: str | None
    ) -> None:
        config = _resolve(
            {"repository": "acme/app", "instructions": call}, {"instructions": profile}, {"instructions": team}
        )
        assert config.instructions == expected

    @parameterized.expand([(5, True), (240, True), (4, False), (241, False), (0, False)])
    def test_duration_bounds(self, minutes: int, valid: bool) -> None:
        # The team level, because an API serializer does not check a value that a row already holds.
        if valid:
            assert _resolve({"repository": "acme/app"}, None, {"max_duration_minutes": minutes})
        else:
            with self.assertRaises(InvalidInput) as raised:
                _resolve({"repository": "acme/app"}, None, {"max_duration_minutes": minutes})
            assert raised.exception.attr == "max_duration_minutes"

    def test_webhook_url_and_profile_id(self) -> None:
        config = _resolve({"repository": "acme/app"}, {"webhook_url": "https://example.com/hook"}, {})
        assert config.webhook_url == "https://example.com/hook"
        assert config.profile_id == PROFILE_ID
        assert _resolve({"repository": "acme/app"}, None, {}).profile_id is None

    def test_config_json_round_trip(self) -> None:
        config = _resolve(
            {"repository": "acme/app", "max_cost_usd": Decimal("12.50"), "tags": ["a"], "size": SizeName.S_16X64},
            {"instructions": "Use pnpm"},
            {},
        )
        assert ResolvedRunConfig.from_json(config.to_json()) == config

    @parameterized.expand([("with_instructions", "Use pnpm", True), ("without_instructions", None, False)])
    def test_render_prompt_puts_instructions_above_prompt(
        self, _name: str, instructions: str | None, has_block: bool
    ) -> None:
        config = _resolve({"repository": "acme/app", "instructions": instructions}, None, {})
        rendered = render_prompt(config, "Fix the bug")
        if has_block:
            assert rendered.index("Use pnpm") < rendered.index("Fix the bug")
        else:
            assert rendered == "Fix the bug"

    @parameterized.expand([(SizeName.S_1X2, (1, 2)), (SizeName.S_4X16, (4, 16)), (SizeName.S_16X64, (16, 64))])
    def test_size_shape(self, size: SizeName, expected: tuple[int, int]) -> None:
        assert size_shape(size) == expected
