"""What a caller can select for a run, and what it costs."""

from __future__ import annotations

from decimal import Decimal
from typing import Final

from products.tasks.backend.facade.model_catalogue import offered_model_choices
from products.tasks.backend.facade.pricing import estimate_cloud_agents_compute_usd, get_cloud_agents_rate_card
from products.tasks.backend.facade.run_config import RuntimeAdapter, get_default_model_for_runtime_adapter

from ..facade.contracts import CatalogDTO, EstimateDTO, LimitsDTO, ModelDTO, RateCardDTO
from ..facade.enums import InferenceMode, SizeName
from .limits import create_rate_per_hour, max_concurrent_runs
from .run_rows import size_spec

_USD_PLACES: Final = Decimal("0.0001")


def get_catalog(team_id: int) -> CatalogDTO:
    rate_card = get_cloud_agents_rate_card()
    default_model = get_default_model_for_runtime_adapter(RuntimeAdapter.CLAUDE.value)
    return CatalogDTO(
        sizes=[size_spec(size) for size in SizeName],
        models=[
            ModelDTO(
                id=choice.model,
                name=choice.label,
                runtime_adapter=choice.runtime_adapter,
                is_default=choice.model == default_model,
            )
            for choice in offered_model_choices()
        ],
        inference_modes=list(InferenceMode),
        rates=RateCardDTO(
            vcpu_hour_usd=rate_card.vcpu_hour_usd,
            memory_gib_hour_usd=rate_card.memory_gib_hour_usd,
            version=rate_card.version,
        ),
        limits=LimitsDTO(
            max_concurrent_runs=max_concurrent_runs(team_id),
            create_rate_per_hour=create_rate_per_hour(team_id),
        ),
    )


def estimate_cost(size: SizeName, minutes: int) -> EstimateDTO:
    """The compute price of a sandbox of this size that is up for `minutes`. Model usage is not in it."""
    spec = size_spec(size)
    estimate = estimate_cloud_agents_compute_usd(spec.vcpu, spec.memory_gib, minutes * 60)
    return EstimateDTO(
        size=size,
        minutes=minutes,
        price_per_hour_usd=spec.price_per_hour_usd,
        estimate_usd=estimate.quantize(_USD_PLACES),
    )
