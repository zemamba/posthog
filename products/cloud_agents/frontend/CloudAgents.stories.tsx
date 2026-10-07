import { Meta, StoryObj } from '@storybook/react'

import { FEATURE_FLAGS } from 'lib/constants'
import { App } from 'scenes/App'
import { urls } from 'scenes/urls'

import type { UserInferenceCredentialApi } from '~/generated/core/api.schemas'
import { mswDecorator } from '~/mocks/browser'
import { toPaginatedResponse } from '~/mocks/handlers'

import type {
    CloudAgentCatalogApi,
    CloudAgentRunApi,
    CloudAgentRunEventsApi,
    CloudAgentSettingsApi,
    CloudAgentSizeApi,
    CloudAgentUsageSummaryApi,
    ProfileApi,
    WebhookDeliveryApi,
    WebhookEndpointApi,
} from './generated/api.schemas'
import { NEW_RUN_SEARCH_PARAM } from './logics/cloudAgentsNewRunLogic'

const SIZES: CloudAgentSizeApi[] = [
    { name: '1x2', vcpu: 1, memory_gib: 2, price_per_hour_usd: '0.066' },
    { name: '2x4', vcpu: 2, memory_gib: 4, price_per_hour_usd: '0.132' },
    { name: '2x8', vcpu: 2, memory_gib: 8, price_per_hour_usd: '0.184' },
    { name: '4x8', vcpu: 4, memory_gib: 8, price_per_hour_usd: '0.264' },
    { name: '4x16', vcpu: 4, memory_gib: 16, price_per_hour_usd: '0.368' },
    { name: '8x16', vcpu: 8, memory_gib: 16, price_per_hour_usd: '0.528' },
    { name: '8x32', vcpu: 8, memory_gib: 32, price_per_hour_usd: '0.736' },
    { name: '16x64', vcpu: 16, memory_gib: 64, price_per_hour_usd: '1.472' },
]

const sizeNamed = (name: CloudAgentSizeApi['name']): CloudAgentSizeApi => SIZES.find((size) => size.name === name)!

const catalog: CloudAgentCatalogApi = {
    sizes: SIZES,
    models: [
        { id: 'claude-sonnet', name: 'Claude Sonnet', runtime_adapter: 'claude', is_default: true },
        { id: 'claude-opus', name: 'Claude Opus', runtime_adapter: 'claude', is_default: false },
        { id: 'gpt-codex', name: 'GPT Codex', runtime_adapter: 'codex', is_default: false },
    ],
    inference_modes: ['auto', 'own_key', 'own_subscription', 'posthog'],
    rates: { vcpu_hour_usd: '0.040', memory_gib_hour_usd: '0.013', version: '2026-09' },
    limits: { max_concurrent_runs: 5, create_rate_per_hour: 60 },
}

const settings: CloudAgentSettingsApi = {
    repository: 'acme/web',
    branch: null,
    model: null,
    size: '4x16',
    inference: 'auto',
    instructions: 'Run pnpm test before you open the pull request.',
    default_profile: null,
    max_concurrent_runs: 5,
    create_rate_per_hour: 60,
    webhook_secret_set: true,
    updated_at: '2026-09-01T09:00:00Z',
}

const profiles: ProfileApi[] = [
    {
        id: '0199a001-0000-7000-8000-000000000001',
        name: 'dependency-updates',
        description: 'Updates the dependencies each night and fixes what breaks.',
        repository: 'acme/web',
        branch: 'main',
        model: null,
        size: '4x16',
        inference: 'posthog',
        instructions: 'Update one package group in each pull request. Run the full test suite.',
        tags: ['nightly', 'dependencies'],
        webhook_url: null,
        created_by: 1,
        created_at: '2026-08-20T10:00:00Z',
        updated_at: '2026-09-10T14:30:00Z',
    },
    {
        id: '0199a001-0000-7000-8000-000000000002',
        name: 'flaky-test-fixer',
        description: 'Finds the cause of a flaky test and fixes it.',
        repository: 'acme/api',
        branch: null,
        model: 'claude-opus',
        size: '8x32',
        inference: 'own_key',
        instructions: null,
        tags: ['ci'],
        webhook_url: null,
        created_by: 1,
        created_at: '2026-08-28T10:00:00Z',
        updated_at: '2026-09-12T08:15:00Z',
    },
    {
        id: '0199a001-0000-7000-8000-000000000003',
        name: 'docs-sync',
        description: '',
        repository: null,
        branch: null,
        model: null,
        size: null,
        inference: null,
        instructions: null,
        tags: [],
        webhook_url: null,
        created_by: 1,
        created_at: '2026-09-02T10:00:00Z',
        updated_at: '2026-09-02T10:00:00Z',
    },
]

const makeRun = (overrides: Partial<CloudAgentRunApi>): CloudAgentRunApi => ({
    id: '0199b001-0000-7000-8000-000000000001',
    status: 'completed',
    stop_reason: 'done',
    error: null,
    created_at: '2026-09-14T08:00:00Z',
    started_at: '2026-09-14T08:00:20Z',
    completed_at: '2026-09-14T08:19:40Z',
    updated_at: '2026-09-14T08:19:40Z',
    prompt: 'Add a dark mode toggle to the settings page and remember the choice for each user.',
    repository: 'acme/web',
    branch: 'cloud-agents/dark-mode-toggle',
    profile: null,
    config: {
        model: 'claude-sonnet',
        size: sizeNamed('4x16'),
        inference: 'posthog',
        create_pr: true,
        pr_mode: 'draft',
        max_duration_minutes: 120,
        max_cost_usd: null,
        instructions_applied: true,
    },
    result: {
        pr_url: 'https://github.com/acme/web/pull/482',
        pr_urls: ['https://github.com/acme/web/pull/482'],
        summary:
            'Added a dark mode toggle to the settings page. The choice is saved to the user profile and applied on load. All 214 tests pass.',
    },
    cost: {
        compute_usd: '0.1186',
        inference_usd: '0.8420',
        total_usd: '0.9606',
        vcpu_seconds: '4640',
        gib_seconds: '18560',
        billing_mode: 'billed',
        inference_billing: 'posthog',
        final: true,
    },
    agent_sessions: [
        { index: 1, status: 'completed', started_at: '2026-09-14T08:00:20Z', ended_at: '2026-09-14T08:19:40Z' },
    ],
    tags: [],
    metadata: {},
    created_by: { id: 1, email: 'dev@example.com' },
    caller: 'app',
    ...overrides,
})

const completedRun = makeRun({})

const runningRun = makeRun({
    id: '0199b001-0000-7000-8000-000000000002',
    status: 'running',
    stop_reason: null,
    created_at: '2026-09-14T11:47:40Z',
    started_at: '2026-09-14T11:48:00Z',
    completed_at: null,
    prompt: 'Find why the checkout integration test is flaky and fix the cause.',
    repository: 'acme/api',
    branch: 'cloud-agents/flaky-checkout-test',
    profile: { id: profiles[1].id, name: profiles[1].name },
    config: { ...completedRun.config, size: sizeNamed('8x32'), model: 'claude-opus' },
    result: { pr_url: null, pr_urls: [], summary: null },
    cost: {
        compute_usd: '0.1472',
        inference_usd: '0.3105',
        total_usd: '0.4577',
        vcpu_seconds: '5760',
        gib_seconds: '23040',
        billing_mode: 'billed',
        inference_billing: 'posthog',
        final: false,
    },
    agent_sessions: [{ index: 1, status: 'running', started_at: '2026-09-14T11:48:00Z', ended_at: null }],
    tags: ['ci'],
})

const failedRun = makeRun({
    id: '0199b001-0000-7000-8000-000000000003',
    status: 'failed',
    stop_reason: 'error',
    error: 'The agent could not push to the repository because the branch is protected.',
    created_at: '2026-09-13T16:00:00Z',
    started_at: '2026-09-13T16:00:25Z',
    completed_at: '2026-09-13T16:07:05Z',
    prompt: 'Rename the billing module to payments in the whole repository.',
    branch: 'main',
    config: { ...completedRun.config, size: sizeNamed('2x8') },
    result: { pr_url: null, pr_urls: [], summary: null },
    cost: {
        compute_usd: '0.0204',
        inference_usd: '0.1130',
        total_usd: '0.1334',
        vcpu_seconds: '800',
        gib_seconds: '3200',
        billing_mode: 'billed',
        inference_billing: 'posthog',
        final: true,
    },
    agent_sessions: [
        { index: 1, status: 'failed', started_at: '2026-09-13T16:00:25Z', ended_at: '2026-09-13T16:07:05Z' },
    ],
})

const ownKeyRun = makeRun({
    id: '0199b001-0000-7000-8000-000000000004',
    created_at: '2026-09-12T09:30:00Z',
    started_at: '2026-09-12T09:30:18Z',
    completed_at: '2026-09-12T10:12:18Z',
    prompt: 'Move the date helpers to the shared utils package and update each import.',
    branch: 'cloud-agents/shared-date-helpers',
    config: { ...completedRun.config, inference: 'own_key', size: sizeNamed('4x8') },
    result: {
        pr_url: 'https://github.com/acme/web/pull/479',
        pr_urls: ['https://github.com/acme/web/pull/479'],
        summary: 'Moved 14 date helpers to the shared utils package and updated 63 imports.',
    },
    cost: {
        compute_usd: '0.1848',
        inference_usd: null,
        total_usd: '0.1848',
        vcpu_seconds: '10080',
        gib_seconds: '20160',
        billing_mode: 'billed',
        inference_billing: 'own_key',
        final: true,
    },
    agent_sessions: [
        { index: 1, status: 'completed', started_at: '2026-09-12T09:30:18Z', ended_at: '2026-09-12T09:58:00Z' },
        { index: 1, status: 'completed', started_at: '2026-09-12T10:01:00Z', ended_at: '2026-09-12T10:12:18Z' },
    ],
})

const queuedRun = makeRun({
    id: '0199b001-0000-7000-8000-000000000005',
    status: 'queued',
    stop_reason: null,
    created_at: '2026-09-14T11:59:30Z',
    started_at: null,
    completed_at: null,
    prompt: 'Update the dependencies in the mobile group.',
    branch: null,
    profile: { id: profiles[0].id, name: profiles[0].name },
    result: { pr_url: null, pr_urls: [], summary: null },
    cost: {
        compute_usd: '0',
        inference_usd: '0',
        total_usd: '0',
        vcpu_seconds: '0',
        gib_seconds: '0',
        billing_mode: 'billed',
        inference_billing: 'posthog',
        final: false,
    },
    agent_sessions: [],
    created_by: null,
    caller: 'api',
})

const cancelledRun = makeRun({
    id: '0199b001-0000-7000-8000-000000000006',
    status: 'cancelled',
    stop_reason: 'cancelled',
    created_at: '2026-09-11T13:00:00Z',
    started_at: '2026-09-11T13:00:22Z',
    completed_at: '2026-09-11T13:03:02Z',
    prompt: 'Try the new image pipeline on the marketing site.',
    repository: 'acme/marketing',
    branch: null,
    config: { ...completedRun.config, size: sizeNamed('1x2') },
    result: { pr_url: null, pr_urls: [], summary: null },
    cost: {
        compute_usd: '0.0029',
        inference_usd: '0.0210',
        total_usd: '0.0239',
        vcpu_seconds: '160',
        gib_seconds: '320',
        billing_mode: 'unbilled',
        inference_billing: 'posthog',
        final: true,
    },
})

const runs = [queuedRun, runningRun, completedRun, failedRun, ownKeyRun, cancelledRun]

const sessionUpdate = (timestamp: string, update: Record<string, unknown>): Record<string, unknown> => ({
    type: 'notification',
    timestamp,
    notification: { jsonrpc: '2.0', method: 'session/update', params: { update } },
})

const runningEvents: Record<string, unknown>[] = [
    sessionUpdate('2026-09-14T11:48:20Z', {
        sessionUpdate: 'agent_message_chunk',
        content: { type: 'text', text: 'I will run the test a few times to see how it fails.' },
    }),
    sessionUpdate('2026-09-14T11:48:30Z', {
        sessionUpdate: 'tool_call',
        toolCallId: 'call-1',
        title: 'Bash',
        status: 'completed',
        rawInput: { command: 'pytest tests/integration/test_checkout.py --count=20 -x' },
    }),
    sessionUpdate('2026-09-14T11:50:02Z', {
        sessionUpdate: 'tool_call',
        toolCallId: 'call-2',
        title: 'Read',
        status: 'completed',
        rawInput: { file_path: 'tests/integration/test_checkout.py' },
    }),
    sessionUpdate('2026-09-14T11:51:10Z', {
        sessionUpdate: 'agent_message_chunk',
        content: {
            type: 'text',
            text: 'The test fails 3 times in 20. It reads the order before the payment webhook is processed. I will make the test wait for the webhook, and not for a fixed time.',
        },
    }),
    sessionUpdate('2026-09-14T11:51:40Z', { sessionUpdate: 'usage_snapshot', tokens: { input: 18420 } }),
    sessionUpdate('2026-09-14T11:52:00Z', {
        sessionUpdate: 'tool_call',
        toolCallId: 'call-3',
        title: 'Edit',
        status: 'in_progress',
        rawInput: { file_path: 'tests/integration/test_checkout.py' },
    }),
]

/** The stored events of a run: its prompt, then the work of the agent, then how the run ended. */
const eventsFor = (run: CloudAgentRunApi): CloudAgentRunEventsApi => ({
    truncated: false,
    events: [
        { type: 'notification', timestamp: run.created_at, notification: { method: '_posthog/sandbox_ready' } },
        sessionUpdate(run.created_at, {
            sessionUpdate: 'user_message_chunk',
            content: { type: 'text', text: run.prompt },
        }),
        ...(run.id === runningRun.id
            ? runningEvents
            : [
                  sessionUpdate(run.created_at, {
                      sessionUpdate: 'agent_message_chunk',
                      content: { type: 'text', text: 'I will read the code first, then make the change.' },
                  }),
                  sessionUpdate(run.created_at, {
                      sessionUpdate: 'tool_call',
                      toolCallId: 'call-1',
                      title: 'Bash',
                      status: 'completed',
                      rawInput: { command: 'git grep -n "settings" -- src' },
                  }),
                  sessionUpdate(run.created_at, {
                      sessionUpdate: 'tool_call',
                      toolCallId: 'call-2',
                      title: 'Bash',
                      status: run.status === 'failed' ? 'failed' : 'completed',
                      rawInput: { command: 'git push origin HEAD' },
                  }),
                  ...(run.result.summary || run.error
                      ? [
                            sessionUpdate(run.created_at, {
                                sessionUpdate: 'agent_message_chunk',
                                content: { type: 'text', text: run.result.summary ?? run.error },
                            }),
                        ]
                      : []),
              ]),
    ],
})

const usage: CloudAgentUsageSummaryApi = {
    date_from: '2026-08-15T00:00:00Z',
    date_to: '2026-09-14T12:00:00Z',
    group_by: 'day',
    totals: {
        runs: 86,
        compute_usd: '14.2310',
        inference_usd: '51.9040',
        total_usd: '66.1350',
        vcpu_seconds: '612000',
        gib_seconds: '2448000',
    },
    buckets: [
        ['2026-09-14', 4, '0.6120', '2.1040', '2.7160', '26400', '105600'],
        ['2026-09-13', 9, '1.4830', '5.9210', '7.4040', '63900', '255600'],
        ['2026-09-12', 12, '2.0470', '7.3350', '9.3820', '88200', '352800'],
        ['2026-09-11', 7, '1.1260', '3.8800', '5.0060', '48500', '194000'],
        ['2026-09-10', 3, '0.3090', '1.2470', '1.5560', '13300', '53200'],
    ].map(([key, runCount, compute, inference, total, vcpu, gib]) => ({
        key: String(key),
        name: null,
        usage: {
            runs: Number(runCount),
            compute_usd: String(compute),
            inference_usd: String(inference),
            total_usd: String(total),
            vcpu_seconds: String(vcpu),
            gib_seconds: String(gib),
        },
    })),
}

const credentials: UserInferenceCredentialApi[] = [
    {
        kind: 'anthropic_api_key',
        provider: 'anthropic',
        credential_type: 'api_key',
        key_suffix: 'x9Qa',
        created_at: '2026-08-30T10:00:00Z',
        last_used_at: '2026-09-12T10:12:18Z',
    },
]

const webhookEndpoints: WebhookEndpointApi[] = [
    {
        id: '0199c001-0000-7000-8000-000000000001',
        url: 'https://example.com/webhooks/posthog-cloud-agents',
        enabled: true,
        event_types: ['run.completed', 'run.failed'],
        created_by: 1,
        created_at: '2026-09-01T09:00:00Z',
        updated_at: '2026-09-01T09:00:00Z',
    },
    {
        id: '0199c001-0000-7000-8000-000000000002',
        url: 'https://hooks.example.com/ci/agent-events',
        enabled: false,
        event_types: [],
        created_by: 1,
        created_at: '2026-09-05T09:00:00Z',
        updated_at: '2026-09-05T09:00:00Z',
    },
]

const makeDelivery = (overrides: Partial<WebhookDeliveryApi>): WebhookDeliveryApi => ({
    id: '0199d001-0000-7000-8000-000000000001',
    endpoint: webhookEndpoints[0].id,
    url: webhookEndpoints[0].url,
    run_id: completedRun.id,
    event_type: 'run.completed',
    event_id: 'evt_0001',
    status: 'succeeded',
    attempts: 1,
    last_status_code: 200,
    last_error: null,
    next_attempt_at: null,
    delivered_at: '2026-09-14T08:19:42Z',
    created_at: '2026-09-14T08:19:41Z',
    ...overrides,
})

const deliveries: WebhookDeliveryApi[] = [
    makeDelivery({}),
    makeDelivery({
        id: '0199d001-0000-7000-8000-000000000002',
        run_id: failedRun.id,
        event_type: 'run.failed',
        event_id: 'evt_0002',
        status: 'failed',
        attempts: 3,
        last_status_code: 503,
        delivered_at: null,
        created_at: '2026-09-13T16:07:06Z',
    }),
    makeDelivery({
        id: '0199d001-0000-7000-8000-000000000003',
        event_type: 'run.test',
        event_id: 'evt_0003',
        status: 'gave_up',
        attempts: 8,
        last_status_code: null,
        delivered_at: null,
        created_at: '2026-09-10T12:00:00Z',
    }),
]

const BASE = '/api/projects/:team_id/cloud_agents'

/** Every endpoint the scenes call. Each story passes the runs that its list and detail requests return. */
const cloudAgentsDecorator = (storyRuns: CloudAgentRunApi[]): ReturnType<typeof mswDecorator> =>
    mswDecorator({
        get: {
            [`${BASE}/catalog/`]: catalog,
            [`${BASE}/settings/`]: settings,
            [`${BASE}/profiles/`]: toPaginatedResponse(profiles),
            [`${BASE}/profiles/:id/`]: profiles[0],
            [`${BASE}/usage/`]: usage,
            [`${BASE}/runs/`]: toPaginatedResponse(storyRuns),
            [`${BASE}/runs/:id/`]: ({ params }) => {
                const run = storyRuns.find((candidate) => candidate.id === params.id)
                return run
                    ? [200, run]
                    : [404, { type: 'invalid_request', code: 'run_not_found', detail: 'Not found.' }]
            },
            [`${BASE}/runs/:id/events/`]: ({ params }) => {
                const run = storyRuns.find((candidate) => candidate.id === params.id)
                return [200, run ? eventsFor(run) : { events: [], truncated: false }]
            },
            [`${BASE}/webhook_endpoints/`]: toPaginatedResponse(webhookEndpoints),
            [`${BASE}/webhook_endpoints/deliveries/`]: deliveries,
            '/api/users/@me/integrations/inference_credentials/': { results: credentials },
        },
    })

const meta: Meta = {
    component: App,
    title: 'Scenes-App/Cloud agents',
    parameters: {
        layout: 'fullscreen',
        viewMode: 'story',
        mockDate: '2026-09-14T12:00:00Z',
        featureFlags: [FEATURE_FLAGS.CLOUD_AGENTS, FEATURE_FLAGS.CLOUD_AGENTS_CLAUDE_SUBSCRIPTION_STORAGE],
    },
}
export default meta

type Story = StoryObj<{}>

export const RunsList: Story = {
    decorators: [cloudAgentsDecorator(runs)],
    parameters: { pageUrl: urls.cloudAgents() },
}

export const RunsEmpty: Story = {
    decorators: [cloudAgentsDecorator([])],
    parameters: { pageUrl: urls.cloudAgents() },
}

export const NewRunModal: Story = {
    decorators: [cloudAgentsDecorator(runs)],
    parameters: { pageUrl: `${urls.cloudAgents()}?${NEW_RUN_SEARCH_PARAM}=1` },
}

export const RunRunning: Story = {
    decorators: [cloudAgentsDecorator(runs)],
    parameters: { pageUrl: urls.cloudAgentRun(runningRun.id) },
}

export const RunCompletedWithPr: Story = {
    decorators: [cloudAgentsDecorator(runs)],
    parameters: { pageUrl: urls.cloudAgentRun(completedRun.id) },
}

export const RunFailed: Story = {
    decorators: [cloudAgentsDecorator(runs)],
    parameters: { pageUrl: urls.cloudAgentRun(failedRun.id) },
}

export const RunOnOwnKey: Story = {
    decorators: [cloudAgentsDecorator(runs)],
    parameters: { pageUrl: urls.cloudAgentRun(ownKeyRun.id) },
}

export const Profiles: Story = {
    decorators: [cloudAgentsDecorator(runs)],
    parameters: { pageUrl: urls.cloudAgentProfiles() },
}

export const ProfileEdit: Story = {
    decorators: [cloudAgentsDecorator(runs)],
    parameters: { pageUrl: urls.cloudAgentProfile(profiles[0].id) },
}

export const Usage: Story = {
    decorators: [cloudAgentsDecorator(runs)],
    parameters: { pageUrl: urls.cloudAgentsUsage() },
}

export const Settings: Story = {
    decorators: [cloudAgentsDecorator(runs)],
    parameters: { pageUrl: urls.cloudAgentsSettings() },
}
