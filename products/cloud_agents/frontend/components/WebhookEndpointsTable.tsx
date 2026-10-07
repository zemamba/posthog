import { useActions, useValues } from 'kea'

import { IconTrash } from '@posthog/icons'
import { LemonButton, LemonDialog, LemonSwitch, LemonTable, LemonTableColumns, LemonTag } from '@posthog/lemon-ui'

import type { WebhookEndpointApi } from '../generated/api.schemas'
import { cloudAgentsWebhooksLogic } from '../logics/cloudAgentsWebhooksLogic'

export function WebhookEndpointsTable(): JSX.Element {
    const { endpoints, endpointsLoading, busyEndpointIds } = useValues(cloudAgentsWebhooksLogic)
    const { setEndpointEnabled, deleteEndpoint, sendTestEvent } = useActions(cloudAgentsWebhooksLogic)

    const columns: LemonTableColumns<WebhookEndpointApi> = [
        {
            title: 'URL',
            key: 'url',
            render: (_, endpoint) => (
                <span className="break-all" translate="no">
                    {endpoint.url}
                </span>
            ),
        },
        {
            title: 'Events',
            key: 'events',
            render: (_, endpoint) =>
                endpoint.event_types.length === 0 ? (
                    'All events'
                ) : (
                    <div className="flex flex-wrap gap-1" translate="no">
                        {endpoint.event_types.map((eventType) => (
                            <LemonTag key={eventType} size="small">
                                {eventType}
                            </LemonTag>
                        ))}
                    </div>
                ),
        },
        {
            title: 'Enabled',
            key: 'enabled',
            width: 0,
            render: (_, endpoint) => (
                <LemonSwitch
                    checked={endpoint.enabled}
                    onChange={(enabled) => setEndpointEnabled(endpoint, enabled)}
                    disabledReason={busyEndpointIds.includes(endpoint.id) ? 'Saving' : undefined}
                    aria-label={endpoint.enabled ? 'Turn off this endpoint' : 'Turn on this endpoint'}
                    data-attr="cloud-agents-webhook-enabled"
                />
            ),
        },
        {
            key: 'actions',
            width: 0,
            render: (_, endpoint) => {
                const busy = busyEndpointIds.includes(endpoint.id)
                return (
                    <div className="flex items-center gap-1">
                        <LemonButton
                            size="small"
                            type="secondary"
                            className="whitespace-nowrap"
                            loading={busy}
                            disabledReason={busy ? 'A request for this endpoint is in progress' : undefined}
                            onClick={() => sendTestEvent(endpoint)}
                            data-attr="cloud-agents-webhook-test"
                        >
                            Send test event
                        </LemonButton>
                        <LemonButton
                            size="small"
                            status="danger"
                            icon={<IconTrash />}
                            tooltip="Delete endpoint"
                            disabledReason={busy ? 'A request for this endpoint is in progress' : undefined}
                            onClick={() =>
                                LemonDialog.open({
                                    title: 'Delete this endpoint?',
                                    description: `PostHog stops sending events to ${endpoint.url}.`,
                                    primaryButton: {
                                        children: 'Delete endpoint',
                                        status: 'danger',
                                        onClick: () => deleteEndpoint(endpoint),
                                    },
                                    secondaryButton: { children: 'Cancel' },
                                })
                            }
                            data-attr="cloud-agents-webhook-delete"
                        />
                    </div>
                )
            },
        },
    ]

    return (
        <LemonTable
            dataSource={endpoints ?? []}
            columns={columns}
            rowKey="id"
            loading={endpointsLoading}
            emptyState="No endpoints yet. Add a URL below to get an event when a run starts or stops."
            data-attr="cloud-agents-webhook-endpoints"
        />
    )
}
