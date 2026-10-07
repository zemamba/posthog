import { useValues } from 'kea'

import { LemonButton, LemonTag } from '@posthog/lemon-ui'

import { RestrictionScope, useRestrictedArea } from 'lib/components/RestrictedArea'
import { FEATURE_FLAGS, TeamMembershipLevel } from 'lib/constants'
import { featureFlagLogic } from 'lib/logic/featureFlagLogic'
import { urls } from 'scenes/urls'
import { marketingAnalyticsLogic } from 'scenes/web-analytics/tabs/marketing-analytics/frontend/logic/marketingAnalyticsLogic'

import { SourceIcon } from 'products/data_warehouse/frontend/shared/components/SourceIcon'

export function SearchConsoleSource({ search = '' }: { search?: string }): JSX.Element | null {
    const { featureFlags } = useValues(featureFlagLogic)
    const { dataWarehouseSources } = useValues(marketingAnalyticsLogic)
    const restrictedReason = useRestrictedArea({
        scope: RestrictionScope.Project,
        minimumAccessLevel: TeamMembershipLevel.Admin,
    })
    if (
        !featureFlags[FEATURE_FLAGS.MARKETING_ANALYTICS_ORGANIC_KEYWORDS] ||
        !'google search console'.includes(search.trim().toLowerCase())
    ) {
        return null
    }
    const connected = dataWarehouseSources?.results.some((source) => source.source_type === 'GoogleSearchConsole')
    return (
        <div className="border-t p-4 space-y-3" data-attr="marketing-search-console-extra">
            <span className="text-secondary text-xs font-semibold">Also available: organic search</span>
            <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0 flex items-start gap-3 flex-1">
                    <SourceIcon type="GoogleSearchConsole" size="small" disableTooltip />
                    <div className="min-w-0">
                        <div className="flex items-center flex-wrap gap-2">
                            <strong>Google Search Console</strong>
                            {connected && <LemonTag type="info">Connected</LemonTag>}
                        </div>
                        <p className="text-secondary text-sm mb-0 mt-1">
                            See organic search queries, landing pages and average positions in Search performance.
                        </p>
                    </div>
                </div>
                {!connected && (
                    <LemonButton
                        type="secondary"
                        size="small"
                        disabledReason={restrictedReason}
                        to={urls.dataWarehouseSourceNew(
                            'GoogleSearchConsole',
                            urls.marketingAnalyticsApp(),
                            'Marketing analytics'
                        )}
                        targetBlank
                    >
                        Connect
                    </LemonButton>
                )}
            </div>
        </div>
    )
}
