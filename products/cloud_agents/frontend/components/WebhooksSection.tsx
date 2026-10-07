import { useActions, useValues } from 'kea'

import { cloudAgentsWebhooksLogic } from '../logics/cloudAgentsWebhooksLogic'
import { LoadErrorBanner } from './LoadErrorBanner'
import { SettingsSection } from './SettingsSection'
import { WebhookDeliveriesTable } from './WebhookDeliveriesTable'
import { WebhookEndpointForm } from './WebhookEndpointForm'
import { WebhookEndpointsTable } from './WebhookEndpointsTable'
import { WebhookSignatureSnippet } from './WebhookSignatureSnippet'
import { WebhookSigningSecret } from './WebhookSigningSecret'

export function WebhooksSection(): JSX.Element {
    const { endpoints, endpointsLoading, endpointsLoadFailed } = useValues(cloudAgentsWebhooksLogic)
    const { loadEndpoints } = useActions(cloudAgentsWebhooksLogic)

    return (
        <SettingsSection
            title="Webhooks"
            description="PostHog sends a POST request to each endpoint when a run starts, completes, fails or is canceled."
            data-attr="cloud-agents-webhooks"
        >
            {endpoints === null && endpointsLoadFailed ? (
                <LoadErrorBanner what="the endpoints" onRetry={loadEndpoints} retrying={endpointsLoading} />
            ) : (
                <WebhookEndpointsTable />
            )}
            <WebhookEndpointForm />
            <WebhookSigningSecret />
            <WebhookDeliveriesTable />
            <WebhookSignatureSnippet />
        </SettingsSection>
    )
}
