import type { Meta } from '@storybook/react'
import { within } from '@testing-library/dom'

import { FEATURE_FLAGS } from 'lib/constants'
import { AddSourceStep } from 'scenes/marketing-analytics/Onboarding/AddSourceStep'
import { Onboarding } from 'scenes/marketing-analytics/Onboarding/Onboarding'
import type { Suggestion } from 'scenes/web-analytics/tabs/marketing-analytics/frontend/logic/setupPlanLogic'

import { mswDecorator, useStorybookMocks } from '~/mocks/browser'

import { expect, userEvent } from 'storybook/test'

import type { SuggestionApi } from '../generated/api.schemas'
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
        { ...suggestion('GoogleAds', 'google_ads'), title: 'Connect Google Ads' },
        { ...suggestion('MetaAds', 'meta_ads'), title: 'Connect Meta Ads' },
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
                        BingAds: { iconPath: '/static/services/bing.png' },
                        SnapchatAds: { iconPath: '/static/services/snapchat.png' },
                        PinterestAds: { iconPath: '/static/services/pinterest.png' },
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
