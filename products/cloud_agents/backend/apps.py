"""Django app configuration for cloud_agents."""

from django.apps import AppConfig


class CloudAgentsConfig(AppConfig):
    name = "products.cloud_agents.backend"
    label = "cloud_agents"

    def ready(self) -> None:
        # Deferred import: models are not loadable at module import time, and ready() must stay light.
        from products.cloud_agents.backend import receivers  # noqa: PLC0415

        receivers.connect()
