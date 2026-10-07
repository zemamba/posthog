from typing import Any

from unittest.mock import patch

from products.cloud_agents.backend.facade.contracts import CallerIdentity
from products.cloud_agents.backend.facade.enums import CallerKind

FLAG_KEY = "cloud-agents"


class CloudAgentsFlagMixin:
    _flag_patcher: Any

    def setUp(self) -> None:
        super().setUp()  # type: ignore[misc]
        self.set_cloud_agents_flag(True)

    def tearDown(self) -> None:
        self._flag_patcher.stop()
        super().tearDown()  # type: ignore[misc]

    def set_cloud_agents_flag(self, enabled: bool) -> None:
        if hasattr(self, "_flag_patcher"):
            self._flag_patcher.stop()
        self._flag_patcher = patch("posthoganalytics.feature_enabled")
        mock = self._flag_patcher.start()
        # Only this flag, so the request does not turn on unrelated flags.
        mock.side_effect = lambda flag_name, *args, **kwargs: enabled if flag_name == FLAG_KEY else False

    def base_url(self) -> str:
        return f"/api/projects/{self.team.id}/cloud_agents"  # type: ignore[attr-defined]


def caller_for(user: Any) -> CallerIdentity:
    return CallerIdentity(user_id=user.id, distinct_id=user.distinct_id, kind=CallerKind.API, billable=True)
