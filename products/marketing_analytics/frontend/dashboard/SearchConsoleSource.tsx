import { useValues } from 'kea'

import { LemonButton, LemonCard, LemonTag } from '@posthog/lemon-ui'

import { RestrictionScope, useRestrictedArea } from 'lib/components/RestrictedArea'
import { FEATURE_FLAGS, TeamMembershipLevel } from 'lib/constants'
import { featureFlagLogic } from 'lib/logic/featureFlagLogic'
import { urls } from 'scenes/urls'
import { marketingAnalyticsLogic } from 'scenes/web-analytics/tabs/marketing-analytics/frontend/logic/marketingAnalyticsLogic'

import { SourceIcon } from 'products/data_warehouse/frontend/shared/components/SourceIcon'

export function SearchConsoleSource(): JSX.Element | null {
    const { featureFlags } = useValues(featureFlagLogic)
    const { dataWarehouseSources } = useValues(marketingAnalyticsLogic)
    const restrictedReason = useRestrictedArea({
        scope: RestrictionScope.Project,
        minimumAccessLevel: TeamMembershipLevel.Admin,
    })
    if (!featureFlags[FEATURE_FLAGS.MARKETING_ANALYTICS_ORGANIC_KEYWORDS]) {
        return null
    }
    const sources = [
        { type: 'GoogleAds', name: 'Google Ads' },
        { type: 'BingAds', name: 'Bing Ads' },
        { type: 'GoogleSearchConsole', name: 'Google Search Console' },
    ].map((source) => ({
        ...source,
        connected: dataWarehouseSources?.results.some((connection) => connection.source_type === source.type),
    }))
    return (
        <LemonCard
            hoverEffect={false}
            className="max-w-3xl w-full mx-auto mt-4 mb-6 space-y-4"
            data-attr="marketing-search-console-extra"
        >
            <div>
                <h3 className="mb-2">Connect your search sources</h3>
                <p className="text-secondary text-sm mb-0">
                    Google Search Console shows organic queries, landing pages and average positions. Connect Google Ads
                    or Bing Ads to compare paid keywords with organic queries and use spend and conversion data to guide
                    your search ad decisions.
                </p>
            </div>
            <div className="divide-y">
                {sources.map((source) => (
                    <div key={source.type} className="flex flex-wrap items-center justify-between gap-3 py-2">
                        <div className="min-w-0 flex items-center gap-3">
                            <SourceIcon type={source.type} size="small" disableTooltip />
                            <strong>{source.name}</strong>
                            {source.connected && <LemonTag type="info">Connected</LemonTag>}
                        </div>
                        {!source.connected && (
                            <LemonButton
                                type="secondary"
                                size="small"
                                disabledReason={restrictedReason}
                                to={urls.dataWarehouseSourceNew(
                                    source.type,
                                    urls.marketingAnalyticsApp(),
                                    'Marketing analytics'
                                )}
                                targetBlank
                            >
                                Connect
                            </LemonButton>
                        )}
                    </div>
                ))}
            </div>
        </LemonCard>
    )
}
