"""
DRF views for cloud_agents.

Validate JSON via serializers, call facade methods,
return serialized responses. No business logic here.
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from django.http import HttpResponseBase

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response

from posthog.api.mixins import ValidatedRequest, validated_request
from posthog.api.streaming import sse_streaming_response
from posthog.api.utils import action
from posthog.renderers import SafeJSONRenderer, ServerSentEventRenderer

from products.tasks.backend.facade.streams import sse_body_for_server_gateway

from ..facade import api
from ..facade.contracts import (
    InvalidInput,
    ProfileCreateInput,
    ProfileNotFound,
    RunCreateInput,
    RunListFilters,
    RunNotFound,
    WebhookEndpointCreateInput,
    WebhookEndpointNotFound,
)
from .common import CloudAgentsViewSet, caller_from_request, parse_uuid
from .serializers import (
    IDEMPOTENCY_KEY_MAX_LENGTH,
    CloudAgentCatalogSerializer,
    CloudAgentEstimateQuerySerializer,
    CloudAgentEstimateSerializer,
    CloudAgentRunCreateSerializer,
    CloudAgentRunEventsSerializer,
    CloudAgentRunListQuerySerializer,
    CloudAgentRunMessageResponseSerializer,
    CloudAgentRunMessageSerializer,
    CloudAgentRunSerializer,
    CloudAgentRunUsageSerializer,
    CloudAgentSettingsSerializer,
    CloudAgentSettingsUpdateSerializer,
    CloudAgentUsageQuerySerializer,
    CloudAgentUsageSummarySerializer,
    ProfileCreateSerializer,
    ProfileSerializer,
    ProfileUpdateSerializer,
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


def _run_id(pk: str) -> UUID:
    run_id = parse_uuid(pk)
    if run_id is None:
        raise RunNotFound()
    return run_id


IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"
IDEMPOTENCY_REPLAYED_HEADER = "Idempotency-Replayed"


def _idempotency_key(request: Request) -> str | None:
    key = request.headers.get(IDEMPOTENCY_KEY_HEADER)
    if key is None:
        return None
    key = key.strip()
    if not 1 <= len(key) <= IDEMPOTENCY_KEY_MAX_LENGTH:
        raise InvalidInput(
            f"The {IDEMPOTENCY_KEY_HEADER} header must have from 1 to {IDEMPOTENCY_KEY_MAX_LENGTH} characters.",
            attr=IDEMPOTENCY_KEY_HEADER,
        )
    return key


class RunEventStreamRenderer(ServerSentEventRenderer):
    """Passes the frames of the stream through. An error response is not a stream, so it is written as JSON."""

    def render(self, data: Any, accepted_media_type: Any = None, renderer_context: Any = None) -> Any:
        if isinstance(data, (bytes, str)):
            return data
        return json.dumps(data).encode()


class CloudAgentRunViewSet(CloudAgentsViewSet):
    scope_object_read_actions = ["list", "retrieve", "events", "usage"]
    scope_object_write_actions = ["create", "messages", "cancel"]

    @validated_request(
        query_serializer=CloudAgentRunListQuerySerializer,
        summary="List runs",
        description="The runs of the project, newest first.",
        responses={200: OpenApiResponse(response=CloudAgentRunSerializer(many=True))},
    )
    def list(self, request: ValidatedRequest, **kwargs: Any) -> Response:
        runs = api.list_runs(self.team_id, RunListFilters(**request.validated_query_data))
        # A lazy sequence: the paginator counts it and takes one slice, like a queryset.
        page = self.paginate_queryset(runs)
        return self.get_paginated_response(CloudAgentRunSerializer(page, many=True).data)

    @validated_request(
        request_serializer=CloudAgentRunCreateSerializer,
        summary="Start a run",
        description=(
            "Starts a sandbox with a coding agent that works on the prompt in the repository. The response "
            "returns at once with a `queued` run. Read the run, stream its events or register a webhook "
            "to follow it. Send the same `Idempotency-Key` header again to get the same run and not a second one."
        ),
        parameters=[
            OpenApiParameter(
                name=IDEMPOTENCY_KEY_HEADER,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=False,
                description=(
                    f"A key of 1 to {IDEMPOTENCY_KEY_MAX_LENGTH} characters that is unique for this request. A "
                    "repeated request with the same key and the same body returns the first run with status "
                    "200 and the header `Idempotency-Replayed: true`. The same key with a different body gives "
                    "status 422."
                ),
            )
        ],
        responses={
            201: OpenApiResponse(response=CloudAgentRunSerializer, description="The run started."),
            200: OpenApiResponse(
                response=CloudAgentRunSerializer, description="The idempotency key replayed an earlier run."
            ),
        },
    )
    def create(self, request: ValidatedRequest, **kwargs: Any) -> Response:
        run, replayed = api.start_run(
            self.team_id,
            caller_from_request(request),
            RunCreateInput(**request.validated_data),
            _idempotency_key(request),
        )
        if replayed:
            return Response(CloudAgentRunSerializer(run).data, headers={IDEMPOTENCY_REPLAYED_HEADER: "true"})
        return Response(CloudAgentRunSerializer(run).data, status=status.HTTP_201_CREATED)

    @extend_schema(summary="Retrieve a run", responses={200: CloudAgentRunSerializer})
    def retrieve(self, request: Request, pk: str, **kwargs: Any) -> Response:
        return Response(CloudAgentRunSerializer(api.get_run(self.team_id, _run_id(pk))).data)

    @validated_request(
        request_serializer=CloudAgentRunMessageSerializer,
        summary="Send a message to a run",
        description=(
            "Sends a follow-up message. An agent that is at work gets the message in its current session. "
            "A run that stopped starts a new agent session with the message and goes back to `queued`."
        ),
        responses={202: OpenApiResponse(response=CloudAgentRunMessageResponseSerializer)},
    )
    @action(methods=["POST"], detail=True)
    def messages(self, request: ValidatedRequest, pk: str, **kwargs: Any) -> Response:
        result = api.send_message(
            self.team_id, caller_from_request(request), _run_id(pk), request.validated_data["content"]
        )
        return Response(CloudAgentRunMessageResponseSerializer(result).data, status=status.HTTP_202_ACCEPTED)

    @extend_schema(
        summary="Cancel a run",
        description=(
            "Asks the run to stop. The response has status 202 and the run can still be `running` for a "
            "short time. A run that already stopped is returned with status 200."
        ),
        request=None,
        responses={
            202: OpenApiResponse(response=CloudAgentRunSerializer, description="The run is stopping."),
            200: OpenApiResponse(response=CloudAgentRunSerializer, description="The run already stopped."),
        },
    )
    @action(methods=["POST"], detail=True)
    def cancel(self, request: Request, pk: str, **kwargs: Any) -> Response:
        run, accepted = api.cancel_run(self.team_id, caller_from_request(request), _run_id(pk))
        return Response(
            CloudAgentRunSerializer(run).data, status=status.HTTP_202_ACCEPTED if accepted else status.HTTP_200_OK
        )

    @extend_schema(
        summary="Retrieve the usage of a run",
        description="The cost of the run up to now, and each sandbox that it used.",
        responses={200: CloudAgentRunUsageSerializer},
    )
    @action(methods=["GET"], detail=True)
    def usage(self, request: Request, pk: str, **kwargs: Any) -> Response:
        return Response(CloudAgentRunUsageSerializer(api.get_run_usage(self.team_id, _run_id(pk))).data)

    @extend_schema(
        summary="Read the events of a run",
        description=(
            "By default, the response is one JSON object with the stored events of all agent sessions. "
            "To follow a live run, send `Accept: text/event-stream`. The response is then a Server-Sent Events "
            "stream of the current agent session. Its first frame is `event: run` with the ID, the status and "
            "the stop reason of the run. `Last-Event-ID` and `start=latest` apply to the stream only. To resume "
            "after a disconnect, send the `id` of the last event in the `Last-Event-ID` header.\n\n"
            "**SDK consumers**: a generated fetch wrapper buffers the stream. Use the JSON default through it, "
            "and read the stream with a streaming `fetch` or an `EventSource` client."
        ),
        parameters=[
            OpenApiParameter(
                name="format",
                type=OpenApiTypes.STR,
                enum=["json"],
                location=OpenApiParameter.QUERY,
                required=False,
                description="`json` returns the stored events as one JSON object. This is the default.",
            ),
            OpenApiParameter(
                name="start",
                type=OpenApiTypes.STR,
                enum=["latest"],
                location=OpenApiParameter.QUERY,
                required=False,
                description="Applies to the stream only: `latest` skips the stored events and sends only new events.",
            ),
            OpenApiParameter(
                name="Last-Event-ID",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.HEADER,
                required=False,
                description=(
                    "Applies to the stream only: the `id` of the last event that you received. The stream sends "
                    "the events after it."
                ),
            ),
        ],
        responses={
            (200, "application/json"): CloudAgentRunEventsSerializer,
            (200, "text/event-stream"): OpenApiTypes.STR,
        },
    )
    @action(methods=["GET"], detail=True, renderer_classes=[SafeJSONRenderer, RunEventStreamRenderer])
    def events(self, request: Request, pk: str, **kwargs: Any) -> HttpResponseBase:
        run_id = _run_id(pk)
        if isinstance(request.accepted_renderer, SafeJSONRenderer):
            return Response(CloudAgentRunEventsSerializer(api.get_run_events(self.team_id, run_id)).data)
        stream = api.prepare_run_event_stream(
            self.team_id,
            run_id,
            last_event_id=request.headers.get("Last-Event-ID"),
            start_latest=request.query_params.get("start") == "latest",
        )
        # Releases the request-thread DB connection before the long-lived stream begins. See
        # sse_streaming_response. The stream body is Redis and object storage only, so it never
        # re-acquires one.
        return sse_streaming_response(
            sse_body_for_server_gateway(lambda: api.run_event_stream(stream)),
            endpoint="cloud_agent_run_events",
        )


class CloudAgentsCatalogViewSet(CloudAgentsViewSet):
    """Project-level reads at `cloud_agents/catalog`, `cloud_agents/estimate` and `cloud_agents/usage`."""

    scope_object_read_actions = ["catalog", "estimate", "usage"]
    scope_object_write_actions: list[str] = []

    @extend_schema(
        summary="Retrieve the cloud agents catalog",
        description="The sizes, models and inference modes that a run can use, with the prices and the limits.",
        responses={200: CloudAgentCatalogSerializer},
    )
    @action(methods=["GET"], detail=False, pagination_class=None)
    def catalog(self, request: Request, **kwargs: Any) -> Response:
        return Response(CloudAgentCatalogSerializer(api.get_catalog(self.team_id)).data)

    @validated_request(
        query_serializer=CloudAgentEstimateQuerySerializer,
        summary="Estimate the compute cost of a run",
        description="The compute cost of a sandbox of one size for a number of minutes. Model usage is not included.",
        responses={200: OpenApiResponse(response=CloudAgentEstimateSerializer)},
    )
    @action(methods=["GET"], detail=False, pagination_class=None)
    def estimate(self, request: ValidatedRequest, **kwargs: Any) -> Response:
        query = request.validated_query_data
        return Response(CloudAgentEstimateSerializer(api.estimate_cost(query["size"], query["minutes"])).data)

    @validated_request(
        query_serializer=CloudAgentUsageQuerySerializer,
        summary="Retrieve cloud agents usage",
        description="Cost and usage totals of the runs created in a date range, for each day or for each profile.",
        responses={200: OpenApiResponse(response=CloudAgentUsageSummarySerializer)},
    )
    @action(methods=["GET"], detail=False, pagination_class=None)
    def usage(self, request: ValidatedRequest, **kwargs: Any) -> Response:
        query = request.validated_query_data
        summary = api.get_usage_summary(
            self.team_id,
            date_from=query.get("date_from"),
            date_to=query.get("date_to"),
            group_by=query["group_by"],
        )
        return Response(CloudAgentUsageSummarySerializer(summary).data)


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
        responses={200: CloudAgentSettingsSerializer},
    )
    @action(methods=["GET"], detail=False, url_path="settings", pagination_class=None)
    def team_settings(self, request: Request, **kwargs: Any) -> Response:
        return Response(CloudAgentSettingsSerializer(api.get_team_settings(self.team_id)).data)

    @team_settings.mapping.patch
    @validated_request(
        request_serializer=CloudAgentSettingsUpdateSerializer,
        summary="Update cloud agent settings",
        description="Only the fields in the request change. A null value clears a default.",
        responses={200: OpenApiResponse(response=CloudAgentSettingsSerializer)},
    )
    def update_team_settings(self, request: ValidatedRequest, **kwargs: Any) -> Response:
        changes = dict(request.validated_data)
        if "default_profile" in changes:
            changes["default_profile_id"] = changes.pop("default_profile")
        settings = api.update_team_settings(self.team_id, changes, caller_from_request(request))
        return Response(CloudAgentSettingsSerializer(settings).data)


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
