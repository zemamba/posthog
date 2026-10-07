import { useActions, useValues } from 'kea'

import { useOnMountEffect } from 'lib/hooks/useOnMountEffect'
import { eventUsageLogic } from 'lib/utils/eventUsageLogic'
import { teamLogic } from 'scenes/teamLogic'

import { ProductIntentContext, ProductKey } from '~/queries/schema/schema-general'

import { DetectedSources } from 'products/marketing_analytics/frontend/dashboard/DetectedSources'

import { MarketingAnalyticsSourceStatusBanner } from '../../web-analytics/tabs/marketing-analytics/frontend/components/MarketingAnalyticsSourceStatusBanner'
import { marketingAnalyticsLogic } from '../../web-analytics/tabs/marketing-analytics/frontend/logic/marketingAnalyticsLogic'
import { AddSourceStep } from './AddSourceStep'

export function Onboarding({ completeOnboarding }: { completeOnboarding: () => void }): JSX.Element {
    const { reportMarketingAnalyticsOnboardingViewed, reportMarketingAnalyticsOnboardingCompleted } =
        useActions(eventUsageLogic)
    const { addProductIntent } = useActions(teamLogic)
    const { hasSources } = useValues(marketingAnalyticsLogic)

    useOnMountEffect(() => {
        reportMarketingAnalyticsOnboardingViewed()
    })

    const handleComplete = (): void => {
        reportMarketingAnalyticsOnboardingCompleted(hasSources)
        addProductIntent({
            product_type: ProductKey.MARKETING_ANALYTICS,
            intent_context: ProductIntentContext.MARKETING_ANALYTICS_ONBOARDING_COMPLETED,
            metadata: { has_sources: hasSources },
        })
        completeOnboarding()
    }

    return (
        <div className="space-y-4">
            <MarketingAnalyticsSourceStatusBanner />
            <DetectedSources />
            <AddSourceStep onContinue={handleComplete} hasSources={hasSources} />
        </div>
    )
}
