import type { Meta } from '@storybook/react'

import { FEATURE_FLAGS } from 'lib/constants'
import { Onboarding } from 'scenes/marketing-analytics/Onboarding/Onboarding'

import { useStorybookMocks } from '~/mocks/browser'

import type { SuggestionApi } from '../generated/api.schemas'

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
    suggestions: [suggestion('GoogleAds', 'google_ads'), suggestion('MetaAds', 'meta_ads')],
    readiness: [],
    degraded: [],
    truncated: false,
    summary: 'Connect your ad platforms.',
}

const meta: Meta = {
    title: 'Scenes-App/Marketing Analytics/Source onboarding',
    parameters: {
        layout: 'padded',
        featureFlags: [FEATURE_FLAGS.MARKETING_ANALYTICS_NEW_DASHBOARD, FEATURE_FLAGS.MARKETING_ANALYTICS_SETUP],
    },
}
export default meta

export function DetectedPlatforms(): JSX.Element {
    useStorybookMocks({ get: { '/api/projects/:team_id/marketing_analytics/setup_plan/': () => [200, plan] } })
    return <Onboarding completeOnboarding={() => {}} />
}

export function NoDetectedPlatforms(): JSX.Element {
    useStorybookMocks({
        get: { '/api/projects/:team_id/marketing_analytics/setup_plan/': () => [200, { ...plan, suggestions: [] }] },
    })
    return <Onboarding completeOnboarding={() => {}} />
}

export function Scanning(): JSX.Element {
    useStorybookMocks({
        get: { '/api/projects/:team_id/marketing_analytics/setup_plan/': () => new Promise(() => {}) },
    })
    return <Onboarding completeOnboarding={() => {}} />
}
Scanning.parameters = { testOptions: { waitForLoadersToDisappear: false } }

export function Narrow(): JSX.Element {
    useStorybookMocks({ get: { '/api/projects/:team_id/marketing_analytics/setup_plan/': () => [200, plan] } })
    return (
        <div className="max-w-lg">
            <Onboarding completeOnboarding={() => {}} />
        </div>
    )
}
