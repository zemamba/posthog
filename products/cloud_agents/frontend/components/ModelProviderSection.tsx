import { useActions, useValues } from 'kea'

import { LemonBanner, LemonSkeleton } from '@posthog/lemon-ui'

import { useFeatureFlag } from 'lib/hooks/useFeatureFlag'

import { InferenceCredentialKindEnumApi } from '~/generated/core/api.schemas'

import { inferenceCredentialsLogic } from '../logics/inferenceCredentialsLogic'
import { LoadErrorBanner } from './LoadErrorBanner'
import { ModelProviderKind, ModelProviderRow } from './ModelProviderRow'
import { SettingsSection } from './SettingsSection'

const API_KEY_PROVIDERS: ModelProviderKind[] = [
    {
        kind: InferenceCredentialKindEnumApi.AnthropicApiKey,
        name: 'Anthropic API key',
        hint: 'Create a key in the Anthropic console. We check it with Anthropic before we save it.',
        placeholder: 'sk-ant-...',
    },
    {
        kind: InferenceCredentialKindEnumApi.OpenaiApiKey,
        name: 'OpenAI API key',
        hint: 'Create a key in the OpenAI platform settings. We check it with OpenAI before we save it.',
        placeholder: 'sk-...',
    },
]

const CLAUDE_SUBSCRIPTION: ModelProviderKind = {
    kind: InferenceCredentialKindEnumApi.ClaudeSubscription,
    name: 'Claude subscription',
    hint: 'Run "claude setup-token" in a terminal and paste the token that it prints.',
    placeholder: 'The token from claude setup-token',
}

export function ModelProviderSection(): JSX.Element {
    const { credentials, credentialsLoading, credentialsLoadFailed } = useValues(inferenceCredentialsLogic)
    const { loadCredentials } = useActions(inferenceCredentialsLogic)
    const subscriptionEnabled = useFeatureFlag('CLOUD_AGENTS_CLAUDE_SUBSCRIPTION_STORAGE')
    const providers = subscriptionEnabled ? [...API_KEY_PROVIDERS, CLAUDE_SUBSCRIPTION] : API_KEY_PROVIDERS

    return (
        <SettingsSection
            title="Your model provider"
            description={
                <>
                    These credentials belong to you and no one else in the project can use them. With the automatic
                    option, a run uses your API key first, then your subscription, then PostHog AI credits. When a run
                    asks for one option by name, it uses only that one and fails if it is not connected.
                </>
            }
            data-attr="cloud-agents-model-provider"
        >
            <LemonBanner type="warning" className="max-w-180">
                The agent runs code in the sandbox, and that code may be able to read the credential the run uses.
                Connect a key that you can revoke, and set a spend limit on it with your provider.
            </LemonBanner>
            {credentials === null && credentialsLoadFailed ? (
                <LoadErrorBanner what="your credentials" onRetry={loadCredentials} retrying={credentialsLoading} />
            ) : credentials === null ? (
                <LemonSkeleton className="h-32 max-w-180" />
            ) : (
                <div className="flex max-w-180 flex-col gap-3">
                    {providers.map((provider) => (
                        <ModelProviderRow key={provider.kind} provider={provider} />
                    ))}
                </div>
            )}
        </SettingsSection>
    )
}
