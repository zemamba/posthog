import type { Meta } from '@storybook/react'
import { within } from '@testing-library/dom'
import { useActions } from 'kea'
import { useEffect } from 'react'

import { FEATURE_FLAGS } from 'lib/constants'
import { AddSourceStep } from 'scenes/marketing-analytics/Onboarding/AddSourceStep'
import { marketingOnboardingLogic } from 'scenes/marketing-analytics/Onboarding/marketingOnboardingLogic'
import { Onboarding } from 'scenes/marketing-analytics/Onboarding/Onboarding'
import type { Suggestion } from 'scenes/web-analytics/tabs/marketing-analytics/frontend/logic/setupPlanLogic'

import { mswDecorator, useStorybookMocks } from '~/mocks/browser'
import { NodeKind } from '~/queries/schema/schema-general'

import { expect, userEvent } from 'storybook/test'

import type { SuggestionApi } from '../generated/api.schemas'
import { NewMarketingAnalyticsDashboard } from './NewMarketingAnalyticsDashboard'
import { SourceOnboardingScan, SourceOnboardingScanProps } from './SourceOnboardingScan'

const suggestion = (kind: string, integration: string): SuggestionApi => ({
    id: `connect_source:${integration}`,
    kind: 'connect_source',
    integration,
    severity: 'warning',
    confidence: 1,
    source: 'deterministic',
    title: `Connect ${kind}`,
    evidence: `Events include campaign tracking from ${kind}.`,
    unlocks: ['cost'],
    apply: { op: 'open_source_wizard', kind },
    also_recommended: [],
    safe_to_batch: false,
    rank_score: 1,
    deep_link: null,
    docs_url: null,
    spend_at_risk: 0,
    event_volume: 12,
})

const plan = {
    suggestions: [
        {
            ...suggestion('GoogleAds', 'google_ads'),
            title: 'Connect Google Ads',
            evidence: 'Events include campaign tracking from Google Ads.',
        },
        {
            ...suggestion('MetaAds', 'meta_ads'),
            title: 'Connect Meta Ads',
            evidence: 'Events include campaign tracking from Meta Ads.',
        },
    ],
    readiness: [],
    degraded: [],
    truncated: false,
    summary: 'Connect your ad platforms.',
}

const meta: Meta = {
    title: 'Scenes-App/Marketing Analytics/Source onboarding',
    component: SourceOnboardingScan,
    parameters: {
        layout: 'padded',
        featureFlags: [FEATURE_FLAGS.MARKETING_ANALYTICS_NEW_DASHBOARD, FEATURE_FLAGS.MARKETING_ANALYTICS_SETUP],
    },
    decorators: [
        mswDecorator({
            get: {
                '/api/environments/:team_id/external_data_sources/wizard/': () => [
                    200,
                    {
                        GoogleAds: { iconPath: '/static/services/google-ads.png' },
                        MetaAds: { iconPath: '/static/services/meta-ads.png' },
                        LinkedinAds: { iconPath: '/static/services/linkedin.png' },
                        TikTokAds: { iconPath: '/static/services/tiktok.png' },
                        RedditAds: { iconPath: '/static/services/reddit.png' },
                        BingAds: { iconPath: '/static/services/bing-ads.svg' },
                        SnapchatAds: { iconPath: '/static/services/snapchat.png' },
                        PinterestAds: { iconPath: '/static/services/pinterest_ads.png' },
                        BigQuery: { iconPath: '/static/services/bigquery.png' },
                    },
                ],
            },
        }),
    ],
}
export default meta

const scanProps: SourceOnboardingScanProps = {
    loading: false,
    failed: false,
    suggestions: plan.suggestions as Suggestion[],
    onManual: () => {},
    onContinue: () => {},
    onRescan: () => {},
}

export function DetectedPlatforms(): JSX.Element {
    return <SourceOnboardingScan {...scanProps} />
}
export function Scanning(): JSX.Element {
    return <SourceOnboardingScan {...scanProps} loading />
}
Scanning.parameters = { testOptions: { waitForLoadersToDisappear: false } }
export function NoDetectedPlatforms(): JSX.Element {
    return <SourceOnboardingScan {...scanProps} suggestions={[]} />
}
export function ScanFailed(): JSX.Element {
    return <SourceOnboardingScan {...scanProps} failed suggestions={[]} />
}
export function ManualSelection(): JSX.Element {
    return <AddSourceStep onContinue={() => {}} hasSources={false} />
}
export function Narrow(): JSX.Element {
    return (
        <div className="max-w-lg">
            <SourceOnboardingScan {...scanProps} />
        </div>
    )
}

export function SkipDuringScan(): JSX.Element {
    useStorybookMocks({
        get: { '/api/projects/:team_id/marketing_analytics/setup_plan/': () => new Promise(() => {}) },
    })
    return <Onboarding completeOnboarding={() => {}} />
}
SkipDuringScan.parameters = { testOptions: { waitForLoadersToDisappear: false } }
SkipDuringScan.play = async ({ canvasElement }: { canvasElement: HTMLElement }): Promise<void> => {
    const canvas = within(canvasElement)
    await userEvent.click(await canvas.findByRole('button', { name: 'Skip and add manually' }))
    await expect(canvas.findByText('Native integrations (recommended)')).resolves.toBeVisible()
    expect(canvas.queryByText('Scanning events from the last 7 days')).not.toBeInTheDocument()
}

export function DashboardWithoutSources(): JSX.Element {
    useStorybookMocks({
        get: {
            '/api/projects/:team_id/marketing_analytics/setup_plan/': () => [200, { ...plan, suggestions: [] }],
            '/api/environments/:team_id/external_data_sources/': () => [200, { results: [] }],
            '/api/projects/:team_id/marketing_analytics/source_validation/': () => [200, { errors_by_source: {} }],
            '/api/projects/:team_id/marketing_analytics/utm_audit/': () => [
                200,
                {
                    total_campaigns: 0,
                    campaigns_with_issues: 0,
                    campaigns_without_issues: 0,
                    total_spend_at_risk: 0,
                    results: [],
                    all_utm_events: [],
                },
            ],
        },
        post: {
            '/api/environments/:team_id/query/:kind/': async ({ request }) => {
                const { query } = (await request.json()) as { query: { kind: string } }
                if (query.kind === NodeKind.DatabaseSchemaQuery) {
                    return [200, { tables: {} }]
                }
                if (query.kind === NodeKind.WebOverviewQuery) {
                    return [
                        200,
                        {
                            results: [
                                { key: 'visitors', kind: 'unit', value: 128, previous: null },
                                { key: 'views', kind: 'unit', value: 240, previous: null },
                                { key: 'sessions', kind: 'unit', value: 156, previous: null },
                            ],
                        },
                    ]
                }
                if (query.kind === NodeKind.TrendsQuery) {
                    return [
                        200,
                        {
                            results: [
                                {
                                    label: 'Visitors',
                                    days: [
                                        '2026-09-10',
                                        '2026-09-11',
                                        '2026-09-12',
                                        '2026-09-13',
                                        '2026-09-14',
                                        '2026-09-15',
                                        '2026-09-16',
                                    ],
                                    data: [18, 17, 20, 19, 16, 18, 20],
                                },
                            ],
                        },
                    ]
                }
                if (query.kind === NodeKind.WebStatsTableQuery) {
                    return [
                        200,
                        {
                            columns: [
                                'context.columns.breakdown_value',
                                'context.columns.visitors',
                                'context.columns.views',
                                'context.columns.sessions',
                            ],
                            results: [['Direct', [128, 100], [240, 200], [156, 120]]],
                        },
                    ]
                }
                return [200, { results: [] }]
            },
        },
    })
    const { completeOnboarding } = useActions(marketingOnboardingLogic)
    useEffect(() => completeOnboarding(), [completeOnboarding])
    return <NewMarketingAnalyticsDashboard />
}
DashboardWithoutSources.parameters = { mockDate: '2026-09-16' }
DashboardWithoutSources.play = async ({ canvasElement }: { canvasElement: HTMLElement }): Promise<void> => {
    const canvas = within(canvasElement)
    await expect(canvas.findByText(/Connect a marketing source to see spend and ad performance/)).resolves.toBeVisible()
    expect((await canvas.findAllByText('128'))[0]).toBeVisible()
    expect(canvas.queryByRole('button', { name: 'Continue to dashboard' })).not.toBeInTheDocument()
}
