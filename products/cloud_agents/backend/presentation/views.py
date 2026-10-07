"""
DRF views for cloud_agents.

Validate JSON via serializers, call facade methods,
return serialized responses. No business logic here.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from posthog.api.mixins import ValidatedRequest, validated_request
from posthog.api.utils import action

from ..facade import api
from ..facade.contracts import ProfileCreateInput, ProfileNotFound, WebhookEndpointCreateInput, WebhookEndpointNotFound
from .common import CloudAgentsViewSet, caller_from_request, parse_uuid
from .serializers import (
    ProfileCreateSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
    SettingsSerializer,
    SettingsUpdateSerializer,
    WebhookDeliverySerializer,
    WebhookEndpointCreateSerializer,
    WebhookEndpointSerializer,
    WebhookEndpointUpdateSerializer,
    WebhookSecretSerializer,
    WebhookTestSerializer,
)


def _profile_id(pk: str) -> UUID:
    profile_id = parse_uuid(pk)
    if profile_id is None:
        raise ProfileNotFound()
    return profile_id


def _endpoint_id(pk: str) -> UUID:
    endpoint_id = parse_uuid(pk)
    if endpoint_id is None:
        raise WebhookEndpointNotFound()
    return endpoint_id


class CloudAgentProfileViewSet(CloudAgentsViewSet):
    scope_object_read_actions = ["list", "retrieve"]
    scope_object_write_actions = ["create", "partial_update", "destroy"]

    @extend_schema(summary="List profiles", responses={200: ProfileSerializer(many=True)})
    def list(self, request: Request, **kwargs: Any) -> Response:
        profiles = api.list_profiles(self.team_id)
        page = self.paginate_queryset(profiles)
        if page is not None:
            return self.get_paginated_response(ProfileSerializer(page, many=True).data)
        return Response(ProfileSerializer(profiles, many=True).data)

    @validated_request(
        request_serializer=ProfileCreateSerializer,
        summary="Create a profile",
        description="A profile is a named set of run defaults. A run names a profile to use its defaults.",
        responses={201: OpenApiResponse(response=ProfileSerializer)},
    )
    def create(self, request: ValidatedRequest, **kwargs: Any) -> Response:
        profile = api.create_profile(
            self.team_id, ProfileCreateInput(**request.validated_data), caller_from_request(request)
        )
        return Response(ProfileSerializer(profile).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Retrieve a profile", responses={200: ProfileSerializer})
    def retrieve(self, request: Request, pk: str, **kwargs: Any) -> Response:
        return Response(ProfileSerializer(api.get_profile(self.team_id, _profile_id(pk))).data)

    @validated_request(
        request_serializer=ProfileUpdateSerializer,
        summary="Update a profile",
        description="Only the fields in the request change. A null value clears a default.",
        responses={200: OpenApiResponse(response=ProfileSerializer)},
    )
    def partial_update(self, request: ValidatedRequest, pk: str, **kwargs: Any) -> Response:
        profile = api.update_profile(
            self.team_id, _profile_id(pk), request.validated_data, caller_from_request(request)
        )
        return Response(ProfileSerializer(profile).data)

    @extend_schema(
        summary="Delete a profile",
        description="Runs that used the profile keep their configuration. The name becomes free.",
        request=None,
        responses={204: None},
    )
    def destroy(self, request: Request, pk: str, **kwargs: Any) -> Response:
        api.delete_profile(self.team_id, _profile_id(pk), caller_from_request(request))
        return Response(status=status.HTTP_204_NO_CONTENT)


class CloudAgentSettingsViewSet(CloudAgentsViewSet):
    """The settings of the project, a single object at `cloud_agents/settings`.

    The viewset is registered at `cloud_agents` and the action supplies the `settings` path segment,
    because a DRF router gives a collection URL no PATCH route.
    """

    scope_object_read_actions = ["team_settings"]
    scope_object_write_actions = ["update_team_settings"]

    # Not named `settings`: DRF views keep the API settings in that attribute.
    @extend_schema(
        summary="Retrieve cloud agent settings",
        description="The run defaults and the limits of the project.",
        responses={200: SettingsSerializer},
    )
    @action(methods=["GET"], detail=False, url_path="settings", pagination_class=None)
    def team_settings(self, request: Request, **kwargs: Any) -> Response:
        return Response(SettingsSerializer(api.get_team_settings(self.team_id)).data)

    @team_settings.mapping.patch
    @validated_request(
        request_serializer=SettingsUpdateSerializer,
        summary="Update cloud agent settings",
        description="Only the fields in the request change. A null value clears a default.",
        responses={200: OpenApiResponse(response=SettingsSerializer)},
    )
    def update_team_settings(self, request: ValidatedRequest, **kwargs: Any) -> Response:
        changes = dict(request.validated_data)
        if "default_profile" in changes:
            changes["default_profile_id"] = changes.pop("default_profile")
        settings = api.update_team_settings(self.team_id, changes, caller_from_request(request))
        return Response(SettingsSerializer(settings).data)


class CloudAgentsWebhookEndpointViewSet(CloudAgentsViewSet):
    scope_object_read_actions = ["list", "retrieve", "deliveries"]
    scope_object_write_actions = ["create", "partial_update", "destroy", "test", "secret", "rotate_secret"]

    @extend_schema(summary="List webhook endpoints", responses={200: WebhookEndpointSerializer(many=True)})
    def list(self, request: Request, **kwargs: Any) -> Response:
        endpoints = api.list_webhook_endpoints(self.team_id)
        page = self.paginate_queryset(endpoints)
        if page is not None:
            return self.get_paginated_response(WebhookEndpointSerializer(page, many=True).data)
        return Response(WebhookEndpointSerializer(endpoints, many=True).data)

    @validated_request(
        request_serializer=WebhookEndpointCreateSerializer,
        summary="Create a webhook endpoint",
        description=(
            f"PostHog sends run events to the URL as signed POST requests. A project can have "
            f"{api.MAX_WEBHOOK_ENDPOINTS} endpoints."
        ),
        responses={201: OpenApiResponse(response=WebhookEndpointSerializer)},
    )
    def create(self, request: ValidatedRequest, **kwargs: Any) -> Response:
        endpoint = api.create_webhook_endpoint(
            self.team_id, WebhookEndpointCreateInput(**request.validated_data), caller_from_request(request)
        )
        return Response(WebhookEndpointSerializer(endpoint).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Retrieve a webhook endpoint", responses={200: WebhookEndpointSerializer})
    def retrieve(self, request: Request, pk: str, **kwargs: Any) -> Response:
        return Response(WebhookEndpointSerializer(api.get_webhook_endpoint(self.team_id, _endpoint_id(pk))).data)

    @validated_request(
        request_serializer=WebhookEndpointUpdateSerializer,
        summary="Update a webhook endpoint",
        responses={200: OpenApiResponse(response=WebhookEndpointSerializer)},
    )
    def partial_update(self, request: ValidatedRequest, pk: str, **kwargs: Any) -> Response:
        endpoint = api.update_webhook_endpoint(self.team_id, _endpoint_id(pk), request.validated_data)
        return Response(WebhookEndpointSerializer(endpoint).data)

    @extend_schema(summary="Delete a webhook endpoint", request=None, responses={204: None})
    def destroy(self, request: Request, pk: str, **kwargs: Any) -> Response:
        api.delete_webhook_endpoint(self.team_id, _endpoint_id(pk), caller_from_request(request))
        return Response(status=status.HTTP_204_NO_CONTENT)

    @extend_schema(
        summary="Send a test event",
        description="Sends a `run.test` event to the endpoint, also when the endpoint is disabled.",
        request=None,
        responses={202: WebhookTestSerializer},
    )
    @action(methods=["POST"], detail=True)
    def test(self, request: Request, pk: str, **kwargs: Any) -> Response:
        delivery_id = api.send_test_webhook_event(self.team_id, _endpoint_id(pk), caller_from_request(request))
        return Response(WebhookTestSerializer({"delivery_id": delivery_id}).data, status=status.HTTP_202_ACCEPTED)

    @extend_schema(
        summary="Create the webhook signing secret",
        description=(
            "Creates the signing secret of the project and returns it one time. When the project already "
            "has a secret, the response has no secret: rotate the secret to get a new one."
        ),
        request=None,
        responses={200: WebhookSecretSerializer},
    )
    @action(methods=["POST"], detail=False, pagination_class=None)
    def secret(self, request: Request, **kwargs: Any) -> Response:
        return Response(WebhookSecretSerializer(api.get_or_create_webhook_secret(self.team_id)).data)

    @extend_schema(
        summary="Rotate the webhook signing secret",
        description="Replaces the signing secret and returns the new one. The old secret stops working immediately.",
        request=None,
        responses={200: WebhookSecretSerializer},
    )
    @action(methods=["POST"], detail=False, pagination_class=None)
    def rotate_secret(self, request: Request, **kwargs: Any) -> Response:
        return Response(WebhookSecretSerializer(api.rotate_webhook_secret(self.team_id)).data)

    @extend_schema(
        summary="List recent webhook deliveries",
        description="The last 50 deliveries of the project, newest first.",
        responses={200: WebhookDeliverySerializer(many=True)},
    )
    @action(methods=["GET"], detail=False, pagination_class=None)
    def deliveries(self, request: Request, **kwargs: Any) -> Response:
        deliveries = api.list_recent_webhook_deliveries(self.team_id)
        return Response(WebhookDeliverySerializer(deliveries, many=True).data)
