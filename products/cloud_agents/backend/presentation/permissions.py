"""Access control for the cloud_agents API."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from rest_framework.permissions import BasePermission
from rest_framework.request import Request
from rest_framework.views import APIView

from ..facade.access import cloud_agents_enabled

if TYPE_CHECKING:
    from posthog.api.routing import TeamAndOrgViewSetMixin
    from posthog.models.user import User


class CloudAgentsAccessPermission(BasePermission):
    message = "Cloud agents is not available for this organization."

    def has_permission(self, request: Request, view: APIView) -> bool:
        user = request.user
        if not user or not user.is_authenticated:
            return False
        organization = cast("TeamAndOrgViewSetMixin", view).organization
        distinct_id = cast("User", user).distinct_id or str(organization.id)
        return cloud_agents_enabled(distinct_id, str(organization.id))
