import { useActions, useValues } from 'kea'

import { LemonButton } from '@posthog/lemon-ui'

import { teamLogic } from 'scenes/teamLogic'
import {
    SetupSection,
    marketingAnalyticsLogic,
} from 'scenes/web-analytics/tabs/marketing-analytics/frontend/logic/marketingAnalyticsLogic'
import { setupPlanLogic } from 'scenes/web-analytics/tabs/marketing-analytics/frontend/logic/setupPlanLogic'
import { nativeSourceDisplayLabel } from 'scenes/web-analytics/tabs/marketing-analytics/frontend/logic/utils'

import { detectedSourcesLogic } from './detectedSourcesLogic'
import { SourceSetupPanel } from './SourceSetupPanel'

export function DetectedSources(): JSX.Element | null {
    const { visibleSuggestions, setupPlan, setupPlanLoading } = useValues(setupPlanLogic)
    const { loadSetupPlan } = useActions(setupPlanLogic)
    const { currentTeamId } = useValues(teamLogic)
    const { dismissedSourceIds } = useValues(detectedSourcesLogic({ teamId: currentTeamId ?? 0 }))
    const { dismissSource } = useActions(detectedSourcesLogic({ teamId: currentTeamId ?? 0 }))
    const { allAvailableSourcesWithStatus, nativeSources, hasSyncedMarketingSources, loading } =
        useValues(marketingAnalyticsLogic)
    const { openSetup } = useActions(marketingAnalyticsLogic)
    const sources = visibleSuggestions.filter(
        (suggestion) =>
            suggestion.kind === 'connect_source' &&
            suggestion.apply?.op === 'open_source_wizard' &&
            !nativeSources.some((source) => source.source_type === suggestion.apply?.kind) &&
            !allAvailableSourcesWithStatus.some((source) => source.source_type === suggestion.apply?.kind) &&
            !dismissedSourceIds.includes(suggestion.id)
    )
    const connections = nativeSources.map((source) => ({
        id: source.id,
        name: nativeSourceDisplayLabel(source.source_type),
        sourceType: source.source_type,
        status: (source.status === 'Running'
            ? 'Syncing'
            : source.status === 'Failed'
              ? 'Needs attention'
              : 'Connected') as 'Connected' | 'Syncing' | 'Needs attention',
        detail:
            source.status === 'Running'
                ? 'Your first import is running. Spend data will appear when it finishes.'
                : source.status === 'Failed'
                  ? 'The import failed. Open setup to check this connection.'
                  : 'Waiting for the first sync to finish.',
    }))
    const openSources = (): void => openSetup(SetupSection.SOURCES, 'dashboard_source_suggestions')
    if (hasSyncedMarketingSources && !sources.length) {
        return null
    }
    if (hasSyncedMarketingSources) {
        return (
            <div className="mt-4 flex flex-wrap items-center gap-3">
                <span className="text-secondary text-sm">
                    {sources.length} suggested {sources.length === 1 ? 'connection' : 'connections'}
                </span>
                <LemonButton size="small" onClick={openSources}>
                    Review in setup
                </LemonButton>
            </div>
        )
    }
    return (
        <SourceSetupPanel
            state={
                connections.length
                    ? 'waiting'
                    : setupPlanLoading && !setupPlan
                      ? 'scanning'
                      : !setupPlan && !loading
                        ? 'error'
                        : sources.length
                          ? 'suggestions'
                          : 'empty'
            }
            suggestions={sources}
            connections={connections}
            onRetry={() => loadSetupPlan()}
            onDismiss={dismissSource}
            footer={
                <>
                    <LemonButton
                        type={sources.length || connections.length ? 'secondary' : 'primary'}
                        onClick={openSources}
                        data-attr="marketing-dashboard-connect-source"
                    >
                        Browse integrations
                    </LemonButton>
                    {sources.length > 0 && (
                        <LemonButton type="tertiary" onClick={openSources}>
                            Review in setup
                        </LemonButton>
                    )}
                </>
            }
        />
    )
}
