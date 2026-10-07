import type { LemonTagType } from '@posthog/lemon-ui'

import {
    CloudAgentRunStatusEnumApi,
    InferenceBillingEnumApi,
    InferenceModeEnumApi,
    StopReasonEnumApi,
} from '../generated/api.schemas'

export function isRunActive(status: CloudAgentRunStatusEnumApi): boolean {
    return status === CloudAgentRunStatusEnumApi.Queued || status === CloudAgentRunStatusEnumApi.Running
}

export const RUN_STATUS_DISPLAY: Record<CloudAgentRunStatusEnumApi, { label: string; type: LemonTagType }> = {
    [CloudAgentRunStatusEnumApi.Queued]: { label: 'Queued', type: 'default' },
    [CloudAgentRunStatusEnumApi.Running]: { label: 'Running', type: 'highlight' },
    [CloudAgentRunStatusEnumApi.Completed]: { label: 'Completed', type: 'success' },
    [CloudAgentRunStatusEnumApi.Failed]: { label: 'Failed', type: 'danger' },
    [CloudAgentRunStatusEnumApi.Cancelled]: { label: 'Canceled', type: 'muted' },
}

export const STOP_REASON_MESSAGES: Record<StopReasonEnumApi, string> = {
    [StopReasonEnumApi.Done]: 'The agent finished its work.',
    [StopReasonEnumApi.Cancelled]: 'Someone canceled this run.',
    [StopReasonEnumApi.Error]: 'The run stopped because of an error.',
    [StopReasonEnumApi.Timeout]: 'The run reached its time limit and stopped.',
    [StopReasonEnumApi.BudgetExceeded]: 'The run reached its cost limit and stopped.',
    [StopReasonEnumApi.UsageLimit]:
        'The run stopped because this project reached its usage limit. Raise the limit in billing settings, then send a message to resume the run.',
}

export const INFERENCE_MODE_DISPLAY: Record<InferenceModeEnumApi, { label: string; description: string }> = {
    [InferenceModeEnumApi.Auto]: {
        label: 'Automatic',
        description: 'Uses your own key, then your own subscription, then PostHog AI credits.',
    },
    [InferenceModeEnumApi.OwnKey]: {
        label: 'Your API key',
        description: 'Your provider bills the model usage. PostHog charges for compute only.',
    },
    [InferenceModeEnumApi.OwnSubscription]: {
        label: 'Your Claude subscription',
        description: 'Model usage counts against your subscription. PostHog charges for compute only.',
    },
    [InferenceModeEnumApi.Posthog]: {
        label: 'PostHog AI credits',
        description: 'PostHog provides the model and bills the usage in AI credits.',
    },
}

export const INFERENCE_BILLING_LABELS: Record<InferenceBillingEnumApi, string> = {
    [InferenceBillingEnumApi.Posthog]: 'PostHog AI credits',
    [InferenceBillingEnumApi.OwnKey]: 'Your provider, through your API key',
    [InferenceBillingEnumApi.OwnSubscription]: 'Your provider, through your Claude subscription',
}
