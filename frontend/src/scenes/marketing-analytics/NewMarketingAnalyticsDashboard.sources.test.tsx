import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react'

import { marketingOnboardingLogic } from 'scenes/marketing-analytics/Onboarding/marketingOnboardingLogic'
import {
    marketingAnalyticsLogic,
    MarketingAnalyticsTab,
    SetupSection,
} from 'scenes/web-analytics/tabs/marketing-analytics/frontend/logic/marketingAnalyticsLogic'
import { setupPlanLogic } from 'scenes/web-analytics/tabs/marketing-analytics/frontend/logic/setupPlanLogic'

import { useMocks } from '~/mocks/jest'
import { initKeaTests } from '~/test/init'

import { NewMarketingAnalyticsDashboard } from 'products/marketing_analytics/frontend/dashboard/NewMarketingAnalyticsDashboard'

jest.mock('~/queries/Query/Query', () => ({ Query: () => null }))
jest.mock('scenes/web-analytics/tabs/marketing-analytics/frontend/components/AttributionTab/AttributionTable', () => ({
    AttributionTable: () => null,
}))
jest.mock('scenes/web-analytics/tabs/marketing-analytics/frontend/components/AttributionTab/AttributionTab', () => ({
    AttributionTab: () => null,
}))

it('keeps suggestions visible without data and opens their review in Setup', async () => {
    useMocks({
        get: {
            '/api/projects/:team_id/marketing_analytics/setup_plan': () => [
                200,
                {
                    suggestions: [
                        {
                            id: 'connect_source:GoogleAds',
                            kind: 'connect_source',
                            also_recommended: [],
                            title: 'Connect Google Ads',
                            evidence: 'Traffic contains Google Ads tags.',
                            integration: 'GoogleAds',
                            source: 'deterministic',
                            severity: 'info',
                            unlocks: [],
                            apply: { op: 'open_source_wizard', kind: 'GoogleAds' },
                        },
                    ],
                    readiness: [],
                    degraded: [],
                    truncated: false,
                    summary: '',
                },
            ],
        },
    })
    initKeaTests()
    const unmountOnboarding = marketingOnboardingLogic.mount()
    marketingOnboardingLogic.actions.completeOnboarding()
    localStorage.removeItem('marketing-source-suggestions-expanded')
    const unmountMarketing = marketingAnalyticsLogic.mount()
    const unmountSetup = setupPlanLogic.mount()
    const view = render(<NewMarketingAnalyticsDashboard />)
    try {
        await screen.findByText('Connect your ad platforms')
        expect(screen.getByText('Google Ads')).not.toBeNull()
        view.unmount()
        render(<NewMarketingAnalyticsDashboard />)
        expect(screen.getByText('Google Ads')).not.toBeNull()
        fireEvent.click(screen.getByText('Review in setup'))
        await waitFor(() => expect(marketingAnalyticsLogic.values.activeTab).toBe(MarketingAnalyticsTab.SETUP))
        expect(marketingAnalyticsLogic.values.setupSection).toBe(SetupSection.SOURCES)
        fireEvent.click(screen.getByText('Dismiss'))
        await waitFor(() => expect(screen.queryByText('Google Ads')).toBeNull())
    } finally {
        cleanup()
        setupPlanLogic.actions.restoreAllDismissed()
        localStorage.removeItem('marketing-source-suggestions-expanded')
        unmountOnboarding()
        localStorage.removeItem('marketing-analytics-onboarding-completed')
        unmountSetup()
        unmountMarketing()
    }
})
