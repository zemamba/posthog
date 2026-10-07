import { useActions, useValues } from 'kea'
import { Form } from 'kea-forms'

import { LemonButton, LemonInput, LemonInputSelect } from '@posthog/lemon-ui'

import { LemonField } from 'lib/lemon-ui/LemonField'

import { WebhookEventEnumApi } from '../generated/api.schemas'
import { cloudAgentsWebhooksLogic } from '../logics/cloudAgentsWebhooksLogic'

/** The test event goes out only through "Send test event", so an endpoint cannot subscribe to it. */
const SUBSCRIBABLE_EVENTS = Object.values(WebhookEventEnumApi).filter(
    (eventType) => eventType !== WebhookEventEnumApi.Runtest
)

export function WebhookEndpointForm(): JSX.Element {
    const { isNewEndpointSubmitting } = useValues(cloudAgentsWebhooksLogic)
    const { submitNewEndpoint } = useActions(cloudAgentsWebhooksLogic)

    return (
        <Form
            logic={cloudAgentsWebhooksLogic}
            formKey="newEndpoint"
            enableFormOnSubmit
            className="grid grid-cols-1 items-start gap-2 @min-[48rem]/main-content:grid-cols-[2fr_2fr_auto]"
        >
            <LemonField name="url" label="Endpoint URL">
                <LemonInput placeholder="https://example.com/webhooks/posthog" data-attr="cloud-agents-webhook-url" />
            </LemonField>
            <LemonField name="event_types" label="Events" help="Leave empty to get all events.">
                <LemonInputSelect
                    mode="multiple"
                    placeholder="All events"
                    options={SUBSCRIBABLE_EVENTS.map((eventType) => ({ key: eventType, label: eventType }))}
                    data-attr="cloud-agents-webhook-events"
                />
            </LemonField>
            <LemonButton
                type="primary"
                className="@min-[48rem]/main-content:mt-6"
                onClick={submitNewEndpoint}
                loading={isNewEndpointSubmitting}
                disabledReason={isNewEndpointSubmitting ? 'Adding the endpoint' : undefined}
                data-attr="cloud-agents-webhook-add"
            >
                Add endpoint
            </LemonButton>
        </Form>
    )
}
