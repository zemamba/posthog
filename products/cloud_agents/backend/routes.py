from posthog.api.routing import RouterRegistry

from products.cloud_agents.backend.presentation import views

# (URL prefix, viewset, basename). Add the next resource as one more row.
PROJECT_ROUTES = [
    (r"cloud_agents/profiles", views.CloudAgentProfileViewSet, "project_cloud_agents_profiles"),
    # The viewset's `settings` action supplies the last segment: cloud_agents/settings.
    (r"cloud_agents", views.CloudAgentSettingsViewSet, "project_cloud_agents_settings"),
    (r"cloud_agents/webhook_endpoints", views.CloudAgentsWebhookEndpointViewSet, "project_cloud_agents_webhooks"),
]


def register_routes(routers: RouterRegistry) -> None:
    for prefix, viewset, basename in PROJECT_ROUTES:
        routers.projects.register(prefix, viewset, basename, ["team_id"])
