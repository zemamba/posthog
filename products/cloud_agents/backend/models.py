"""
Django models for cloud_agents.

Keep models thin. Business logic belongs in logic/.
Foreign keys to posthog_team and posthog_user have `db_constraint=False`, so
CreateModel takes no lock on those tables. Django still applies `on_delete`.
"""

from django.db import models
from django.db.models.functions import Lower

from posthog.helpers.encrypted_fields import EncryptedTextField
from posthog.models.scoping.root_mixin import TeamScopedRootMixin
from posthog.models.utils import uuid7

from .facade.enums import (
    BillingMode,
    CallerKind,
    CloudAgentRunStatus,
    InferenceBilling,
    InferenceMode,
    PrMode,
    SizeName,
    StopReason,
    WebhookDeliveryStatus,
)

URL_MAX_LENGTH = 2000


class RunDefaultsMixin(models.Model):
    """Run defaults that a profile and the project settings both hold. A null field sets no default."""

    repository = models.CharField(max_length=255, null=True, blank=True)
    branch = models.CharField(max_length=255, null=True, blank=True)
    model = models.CharField(max_length=100, null=True, blank=True)
    size = models.CharField(max_length=16, choices=SizeName.choices, null=True, blank=True)
    inference = models.CharField(max_length=32, choices=InferenceMode.choices, null=True, blank=True)
    instructions = models.TextField(null=True, blank=True)
    create_pr = models.BooleanField(null=True, blank=True)
    pr_mode = models.CharField(max_length=16, choices=PrMode.choices, null=True, blank=True)
    max_duration_minutes = models.PositiveIntegerField(null=True, blank=True)
    max_cost_usd = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        abstract = True


class CloudAgentProfile(RunDefaultsMixin, TeamScopedRootMixin):
    # `objects` (TeamScopedManager) from TeamScopedRootMixin is fail-closed. `all_teams` is the
    # unscoped manager that Django internals use through Meta.default_manager_name.
    all_teams = models.Manager()  # noqa: DJ012

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    team = models.ForeignKey("posthog.Team", on_delete=models.CASCADE, related_name="+", db_constraint=False)
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, default="")
    tags = models.JSONField(default=list, blank=True)
    webhook_url = models.URLField(max_length=URL_MAX_LENGTH, null=True, blank=True)

    deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)

    created_by = models.ForeignKey(
        "posthog.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", db_constraint=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        default_manager_name = "all_teams"
        constraints = [
            models.UniqueConstraint(
                "team",
                Lower("name"),
                condition=models.Q(deleted=False),
                name="cloud_agents_profile_unique_name",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class CloudAgentRun(TeamScopedRootMixin):
    all_teams = models.Manager()  # noqa: DJ012

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    team = models.ForeignKey("posthog.Team", on_delete=models.CASCADE, related_name="+", db_constraint=False)
    created_by = models.ForeignKey(
        "posthog.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", db_constraint=False
    )
    caller_kind = models.CharField(max_length=16, choices=CallerKind.choices, default=CallerKind.API.value)
    caller_product = models.CharField(max_length=40, null=True, blank=True)
    billable = models.BooleanField(default=True)

    # The Tasks product owns these rows. They are plain ids, because this product reads Tasks
    # through its facade and must not join to its tables.
    task_id = models.UUIDField(null=True, blank=True, db_index=True)
    current_task_run_id = models.UUIDField(null=True, blank=True, db_index=True)
    # Items: {index, task_run_id, status, started_at, ended_at}
    agent_sessions = models.JSONField(default=list, blank=True)

    prompt = models.TextField()
    repository = models.CharField(max_length=255)
    branch = models.CharField(max_length=255, null=True, blank=True)
    profile = models.ForeignKey(CloudAgentProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    tags = models.JSONField(default=list, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    idempotency_key = models.CharField(max_length=100, null=True, blank=True)
    request_hash = models.CharField(max_length=64, null=True, blank=True)
    webhook_url = models.URLField(max_length=URL_MAX_LENGTH, null=True, blank=True)

    # Snapshot of the resolved configuration (ResolvedRunConfig.to_json), so a later change to a
    # profile or to the project settings does not change a run that already started.
    config = models.JSONField(default=dict)

    status = models.CharField(
        max_length=16, choices=CloudAgentRunStatus.choices, default=CloudAgentRunStatus.QUEUED.value
    )
    stop_reason = models.CharField(max_length=32, choices=StopReason.choices, null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    pr_url = models.URLField(max_length=URL_MAX_LENGTH, null=True, blank=True)
    pr_urls = models.JSONField(default=list, blank=True)
    summary = models.TextField(null=True, blank=True)

    compute_usd = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    inference_usd = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    vcpu_seconds = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    gib_seconds = models.DecimalField(max_digits=14, decimal_places=3, null=True, blank=True)
    billing_mode = models.CharField(max_length=16, choices=BillingMode.choices, default=BillingMode.BILLED.value)
    inference_billing = models.CharField(max_length=32, choices=InferenceBilling.choices, null=True, blank=True)
    cost_final = models.BooleanField(default=False)

    class Meta:
        default_manager_name = "all_teams"
        constraints = [
            models.UniqueConstraint(
                fields=["team", "idempotency_key"],
                condition=models.Q(idempotency_key__isnull=False),
                name="cloud_agents_run_unique_idempotency_key",
            ),
        ]
        indexes = [
            models.Index(fields=["team", "-created_at"], name="cloud_agents_run_team_created"),
            models.Index(fields=["team", "status"], name="cloud_agents_run_team_status"),
        ]

    def __str__(self) -> str:
        return f"CloudAgentRun({self.id}, {self.status})"


class TeamCloudAgentsConfig(RunDefaultsMixin, TeamScopedRootMixin):
    """Team extension that holds the project defaults and limits. Read it with `logic.team_config.get_team_config`."""

    all_teams = models.Manager()  # noqa: DJ012

    team = models.OneToOneField(
        "posthog.Team", on_delete=models.CASCADE, primary_key=True, related_name="+", db_constraint=False
    )
    default_profile = models.ForeignKey(
        CloudAgentProfile, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    # Staff set these overrides. A null value means the product default in logic/limits.py.
    max_concurrent_runs = models.PositiveIntegerField(null=True, blank=True)
    create_rate_per_hour = models.PositiveIntegerField(null=True, blank=True)

    # Encrypted and not hashed, because signing a delivery needs the raw value.
    webhook_secret = EncryptedTextField(null=True, blank=True)
    webhook_secret_created_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        default_manager_name = "all_teams"

    def __str__(self) -> str:
        return f"TeamCloudAgentsConfig(team={self.team_id})"


class CloudAgentsWebhookEndpoint(TeamScopedRootMixin):
    all_teams = models.Manager()  # noqa: DJ012

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    team = models.ForeignKey("posthog.Team", on_delete=models.CASCADE, related_name="+", db_constraint=False)
    url = models.URLField(max_length=URL_MAX_LENGTH)
    enabled = models.BooleanField(default=True)
    # An empty list means all event types.
    event_types = models.JSONField(default=list, blank=True)
    created_by = models.ForeignKey(
        "posthog.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+", db_constraint=False
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        default_manager_name = "all_teams"

    def __str__(self) -> str:
        return f"CloudAgentsWebhookEndpoint({self.id})"


class CloudAgentsWebhookDelivery(TeamScopedRootMixin):
    all_teams = models.Manager()  # noqa: DJ012

    id = models.UUIDField(primary_key=True, default=uuid7, editable=False)
    team = models.ForeignKey("posthog.Team", on_delete=models.CASCADE, related_name="+", db_constraint=False)
    # Null for a delivery to the `webhook_url` of one run, and for a delivery whose endpoint was deleted.
    endpoint = models.ForeignKey(
        CloudAgentsWebhookEndpoint, on_delete=models.SET_NULL, null=True, blank=True, related_name="+"
    )
    url = models.URLField(max_length=URL_MAX_LENGTH)
    run_id = models.UUIDField()
    event_type = models.CharField(max_length=32)
    event_id = models.UUIDField()
    payload = models.JSONField()
    status = models.CharField(
        max_length=16, choices=WebhookDeliveryStatus.choices, default=WebhookDeliveryStatus.PENDING.value
    )
    attempts = models.PositiveIntegerField(default=0)
    last_status_code = models.PositiveIntegerField(null=True, blank=True)
    # The exception class name only. The text of a transport error can hold the URL.
    last_error = models.CharField(max_length=100, null=True, blank=True)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        default_manager_name = "all_teams"
        indexes = [
            models.Index(fields=["team", "-created_at"], name="cloud_agents_delivery_created"),
        ]

    def __str__(self) -> str:
        return f"CloudAgentsWebhookDelivery({self.id}, {self.status})"
