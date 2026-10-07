"""Access control for the cloud_agents API."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

import posthoganalytics
from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from ..facade.api import FEATURE_FLAG_KEY

if TYPE_CHECKING:
    from posthog.api.routing import TeamAndOrgViewSetMixin
    from posthog.models.user import User


def cloud_agents_flag_enabled(distinct_id: str, organization_id: str) -> bool:
    return bool(
        posthoganalytics.feature_enabled(
            FEATURE_FLAG_KEY,
            distinct_id,
            groups={"organization": organization_id},
            group_properties={"organization": {"id": organization_id}},
            only_evaluate_locally=False,
            send_feature_flag_events=False,
        )
    )


class CloudAgentsAccessPermission(BasePermission):
    message = "Cloud agents is not available for this organization."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        organization = cast("TeamAndOrgViewSetMixin", view).organization
        distinct_id = cast("User", user).distinct_id or str(organization.id)
        return cloud_agents_flag_enabled(distinct_id, str(organization.id))
