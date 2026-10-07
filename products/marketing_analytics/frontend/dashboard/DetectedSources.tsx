import { useActions, useValues } from 'kea'

import { IconChevronDown, IconChevronRight } from '@posthog/icons'
import { LemonBanner, LemonButton, LemonCard, Spinner } from '@posthog/lemon-ui'

import { teamLogic } from 'scenes/teamLogic'
import { urls } from 'scenes/urls'
import {
    SetupSection,
    marketingAnalyticsLogic,
} from 'scenes/web-analytics/tabs/marketing-analytics/frontend/logic/marketingAnalyticsLogic'
import { setupPlanLogic } from 'scenes/web-analytics/tabs/marketing-analytics/frontend/logic/setupPlanLogic'

import { SourceIcon } from 'products/data_warehouse/frontend/shared/components/SourceIcon'

import { detectedSourcesLogic } from './detectedSourcesLogic'

export function DetectedSources(): JSX.Element | null {
    const { visibleSuggestions, setupPlan, setupPlanLoading } = useValues(setupPlanLogic)
    const { currentTeamId } = useValues(teamLogic)
    const logic = detectedSourcesLogic({ teamId: currentTeamId ?? 0 })
    const { notificationDismissed, dismissedSourceIds } = useValues(logic)
    const { dismiss, expand, dismissSource } = useActions(logic)
    const { allAvailableSourcesWithStatus, nativeSources, loading } = useValues(marketingAnalyticsLogic)
    const { openSetup } = useActions(marketingAnalyticsLogic)
    const sources = visibleSuggestions.filter(
        (suggestion) =>
            suggestion.kind === 'connect_source' &&
            suggestion.apply?.op === 'open_source_wizard' &&
            !nativeSources.some((source) => source.source_type === suggestion.apply?.kind) &&
            !allAvailableSourcesWithStatus.some((source) => source.source_type === suggestion.apply?.kind) &&
            !dismissedSourceIds.includes(suggestion.id)
    )
    if (setupPlanLoading) {
        return (
            <LemonBanner type="info">
                <span className="flex items-center gap-2">
                    <Spinner />
                    <span>Scanning events from the last 7 days…</span>
                </span>
            </LemonBanner>
        )
    }
    if (!setupPlan && !loading) {
        return (
            <LemonBanner type="warning">
                Could not scan events. Open setup to choose a source or scan again.
            </LemonBanner>
        )
    }
    if (!loading && !sources.length && !allAvailableSourcesWithStatus.length && !nativeSources.length) {
        return (
            <LemonBanner
                type="info"
                action={{
                    children: 'Connect a source',
                    onClick: () => openSetup(SetupSection.SOURCES, 'dashboard_source_suggestions'),
                }}
            >
                Connect a marketing source to see spend and ad performance. Data will appear after the first sync
                finishes.
            </LemonBanner>
        )
    }
    if (loading || !sources.length) {
        return null
    }
    return (
        <LemonCard hoverEffect={false} className="p-3">
            <LemonButton
                fullWidth
                noPadding
                aria-expanded={!notificationDismissed}
                onClick={notificationDismissed ? expand : dismiss}
            >
                <span className="flex w-full items-center justify-between gap-3 py-1 text-left whitespace-normal">
                    <span className="flex items-center gap-2 font-semibold text-sm">
                        <span className="flex shrink-0 text-base" aria-hidden="true">
                            {notificationDismissed ? <IconChevronRight /> : <IconChevronDown />}
                        </span>
                        <span>We detected these ad sources ({sources.length})</span>
                    </span>
                </span>
            </LemonButton>
            {!notificationDismissed && (
                <>
                    <p className="text-secondary">
                        Connect these platforms to see their spend and ad performance. Their data is missing from the
                        dashboard until you connect them and the first sync finishes. You can keep connecting other
                        platforms while a sync runs.
                    </p>
                    {sources.map((source) => (
                        <div
                            key={source.id}
                            className="flex flex-wrap items-center justify-between gap-4 py-3 border-t"
                        >
                            <div>
                                <div className="flex items-center gap-2">
                                    <SourceIcon type={source.apply?.kind as string} size="small" disableTooltip />
                                    <strong>{source.title}</strong>
                                </div>
                                <p className="text-secondary text-sm mb-0">{source.evidence}</p>
                            </div>
                            <div className="flex flex-wrap gap-2">
                                <LemonButton
                                    type="primary"
                                    size="small"
                                    to={`/project/${currentTeamId}${urls.dataWarehouseSourceNew(source.apply?.kind as string, `/project/${currentTeamId}/marketing`, 'Marketing analytics')}`}
                                    targetBlank
                                >
                                    Connect
                                </LemonButton>
                                <LemonButton size="small" onClick={() => dismissSource(source.id)}>
                                    Dismiss
                                </LemonButton>
                            </div>
                        </div>
                    ))}
                </>
            )}
            <LemonButton
                type="tertiary"
                onClick={() => {
                    openSetup(SetupSection.SOURCES, 'dashboard_source_suggestions')
                }}
            >
                Review in setup
            </LemonButton>
        </LemonCard>
    )
}
