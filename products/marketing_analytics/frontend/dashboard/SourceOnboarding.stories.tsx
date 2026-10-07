import type { Meta } from '@storybook/react'
import { within } from '@testing-library/dom'
import { useActions } from 'kea'
import { useEffect } from 'react'

import { FEATURE_FLAGS } from 'lib/constants'
import { MarketingAnalyticsScene } from 'scenes/marketing-analytics/MarketingAnalyticsScene'
import { AddSourceStep } from 'scenes/marketing-analytics/Onboarding/AddSourceStep'
import { marketingOnboardingLogic } from 'scenes/marketing-analytics/Onboarding/marketingOnboardingLogic'
import { Onboarding } from 'scenes/marketing-analytics/Onboarding/Onboarding'
import { urls } from 'scenes/urls'
import { marketingAnalyticsLogic } from 'scenes/web-analytics/tabs/marketing-analytics/frontend/logic/marketingAnalyticsLogic'
import type { Suggestion } from 'scenes/web-analytics/tabs/marketing-analytics/frontend/logic/setupPlanLogic'

import { mswDecorator, useStorybookMocks } from '~/mocks/browser'
import { MARKETING_INTEGRATION_CONFIGS, NodeKind } from '~/queries/schema/schema-general'

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
                        GoogleSearchConsole: { iconPath: '/static/services/google-search-console.svg' },
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
    return <AddSourceStep onContinue={() => {}} onBack={() => {}} hasSources={false} />
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
    expect(canvas.queryByText('Finding your ad platforms')).not.toBeInTheDocument()
}

function useDashboardWithoutSourcesMocks(
    suggestions: SuggestionApi[] = [],
    scanFailed = false,
    dataReady = false
): void {
    useStorybookMocks({
        get: {
            '/api/projects/:team_id/marketing_analytics/setup_plan/': () =>
                scanFailed ? [500, { detail: 'Could not scan events.' }] : [200, { ...plan, suggestions }],
            '/api/environments/:team_id/external_data_sources/': () => [
                200,
                {
                    results: dataReady
                        ? [
                              {
                                  id: 'demo-google-ready',
                                  source_type: 'GoogleAds',
                                  status: 'Completed',
                                  schemas: [
                                      MARKETING_INTEGRATION_CONFIGS.GoogleAds.campaignTableName,
                                      MARKETING_INTEGRATION_CONFIGS.GoogleAds.statsTableName,
                                  ].map((name) => ({
                                      id: `demo-${name}`,
                                      name,
                                      should_sync: true,
                                      status: 'Completed',
                                      last_synced_at: '2026-09-16T09:00:00Z',
                                  })),
                              },
                          ]
                        : [],
                },
            ],
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
                if (query.kind === NodeKind.MarketingAnalyticsAggregatedQuery) {
                    return [
                        200,
                        {
                            results: {
                                'Total cost': { value: 1250, previous: null, kind: 'currency' },
                                'Total clicks': { value: 2400, previous: null, kind: 'unit' },
                                'Cost per click': { value: 0.52, previous: null, kind: 'currency' },
                                'Click-through rate': { value: 4.8, previous: null, kind: 'percentage' },
                                'Total impressions': { value: 50000, previous: null, kind: 'unit' },
                                'Reported conversions': { value: 96, previous: null, kind: 'unit' },
                            },
                        },
                    ]
                }
                if (query.kind === NodeKind.MarketingAnalyticsTableQuery && dataReady) {
                    const columns = [
                        'ID',
                        'Campaign',
                        'Source',
                        'Cost',
                        'Clicks',
                        'Impressions',
                        'CPC',
                        'CTR',
                        'Reported Conversions',
                        'Reported Conversion Value',
                        'Reported ROAS',
                        'Cost per Reported Conversions',
                    ]
                    const values = [
                        'demo-campaign',
                        'Example campaign',
                        'Google Ads',
                        1250,
                        2400,
                        50000,
                        0.52,
                        4.8,
                        96,
                        4800,
                        3.84,
                        13.02,
                    ]
                    return [
                        200,
                        {
                            columns,
                            results: [
                                values.map((value, index) => ({
                                    key: columns[index],
                                    value,
                                    kind: [3, 6, 9, 11].includes(index)
                                        ? 'currency'
                                        : index === 7
                                          ? 'percentage'
                                          : 'unit',
                                })),
                            ],
                        },
                    ]
                }
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
                                    label: dataReady ? 'Cost' : 'Visitors',
                                    days: [
                                        '2026-09-10',
                                        '2026-09-11',
                                        '2026-09-12',
                                        '2026-09-13',
                                        '2026-09-14',
                                        '2026-09-15',
                                        '2026-09-16',
                                    ],
                                    data: dataReady
                                        ? [150, 175, 180, 165, 200, 185, 195]
                                        : [18, 17, 20, 19, 16, 18, 20],
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
}

export function DashboardWithoutSources(): JSX.Element {
    useDashboardWithoutSourcesMocks()
    const { completeOnboarding } = useActions(marketingOnboardingLogic)
    useEffect(() => completeOnboarding(), [completeOnboarding])
    return <NewMarketingAnalyticsDashboard />
}
DashboardWithoutSources.parameters = { mockDate: '2026-09-16' }
DashboardWithoutSources.play = async ({ canvasElement }: { canvasElement: HTMLElement }): Promise<void> => {
    const canvas = within(canvasElement)
    await expect(canvas.findByText('Choose an ad platform')).resolves.toBeVisible()
    expect((await canvas.findAllByText('128'))[0]).toBeVisible()
    expect(canvas.queryByRole('button', { name: 'Continue to dashboard' })).not.toBeInTheDocument()
}

export function AdPerformanceWithoutSources(): JSX.Element {
    useDashboardWithoutSourcesMocks()
    const { completeOnboarding } = useActions(marketingOnboardingLogic)
    useEffect(() => completeOnboarding(), [completeOnboarding])
    return <MarketingAnalyticsScene />
}
AdPerformanceWithoutSources.parameters = {
    pageUrl: urls.marketingAnalyticsApp(),
    featureFlags: [FEATURE_FLAGS.WEB_ANALYTICS_MARKETING, FEATURE_FLAGS.MARKETING_ANALYTICS_SETUP],
}
AdPerformanceWithoutSources.play = async ({ canvasElement }: { canvasElement: HTMLElement }): Promise<void> => {
    const canvas = within(canvasElement)
    await expect(canvas.findByText('Choose an ad platform')).resolves.toBeVisible()
    expect(canvas.getByText(/No ad platforms were detected/)).toBeVisible()
    expect(canvas.queryByText('Visitors over time')).not.toBeInTheDocument()
    expect(canvas.queryByRole('button', { name: 'Continue to dashboard' })).not.toBeInTheDocument()
}

export function AdPerformanceWithDetectedSources(): JSX.Element {
    useDashboardWithoutSourcesMocks(plan.suggestions)
    const { completeOnboarding } = useActions(marketingOnboardingLogic)
    useEffect(() => completeOnboarding(), [completeOnboarding])
    return <MarketingAnalyticsScene />
}
AdPerformanceWithDetectedSources.parameters = AdPerformanceWithoutSources.parameters
AdPerformanceWithDetectedSources.play = async ({ canvasElement }: { canvasElement: HTMLElement }): Promise<void> => {
    const canvas = within(canvasElement)
    await expect(canvas.findByText('Connect your ad platforms')).resolves.toBeVisible()
    marketingAnalyticsLogic.actions.loadSources()
    expect(canvas.getByText('Connect your ad platforms')).toBeVisible()
    expect(canvas.queryByText('Checking your connections')).not.toBeInTheDocument()
    expect(canvas.queryByText('Visitors over time')).not.toBeInTheDocument()
}

export function AdPerformanceScanFailed(): JSX.Element {
    useDashboardWithoutSourcesMocks([], true)
    const { completeOnboarding } = useActions(marketingOnboardingLogic)
    useEffect(() => completeOnboarding(), [completeOnboarding])
    return <MarketingAnalyticsScene />
}
AdPerformanceScanFailed.parameters = AdPerformanceWithoutSources.parameters
AdPerformanceScanFailed.play = async ({ canvasElement }: { canvasElement: HTMLElement }): Promise<void> => {
    const canvas = within(canvasElement)
    await expect(canvas.findByText('Could not check your events')).resolves.toBeVisible()
    expect(canvas.getByText('Browse integrations')).toBeVisible()
    expect(canvas.getByText('Try again')).toBeVisible()
}

export function AdPerformanceDataAvailable(): JSX.Element {
    useDashboardWithoutSourcesMocks([plan.suggestions[1]], false, true)
    return <MarketingAnalyticsScene />
}
AdPerformanceDataAvailable.parameters = { ...AdPerformanceWithoutSources.parameters, mockDate: '2026-09-16' }
AdPerformanceDataAvailable.play = async ({ canvasElement }: { canvasElement: HTMLElement }): Promise<void> => {
    const canvas = within(canvasElement)
    await expect(canvas.findByText('1 suggested connection')).resolves.toBeVisible()
    await expect(canvas.findByText('Total clicks')).resolves.toBeVisible()
    expect(canvas.queryByText('Checking your connections')).not.toBeInTheDocument()
}

export function ManualSelectionWithSearchConsole(): JSX.Element {
    return <AddSourceStep onContinue={() => {}} onBack={() => {}} hasSources={false} />
}
ManualSelectionWithSearchConsole.parameters = {
    featureFlags: [FEATURE_FLAGS.MARKETING_ANALYTICS_ORGANIC_KEYWORDS, FEATURE_FLAGS.MARKETING_ANALYTICS_SETUP],
}
ManualSelectionWithSearchConsole.play = async ({ canvasElement }: { canvasElement: HTMLElement }): Promise<void> => {
    const canvas = within(canvasElement)
    await expect(canvas.findByText('Google Search Console')).resolves.toBeVisible()
    expect(canvas.getByText('Also available: organic search')).toBeVisible()
}
