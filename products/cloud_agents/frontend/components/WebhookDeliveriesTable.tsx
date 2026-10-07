import { useActions, useValues } from 'kea'

import { IconRefresh } from '@posthog/icons'
import { LemonButton, LemonTable, LemonTableColumns, LemonTag, LemonTagType } from '@posthog/lemon-ui'

import { TZLabel } from 'lib/components/TZLabel'

import type { WebhookDeliveryApi } from '../generated/api.schemas'
import { WebhookDeliveryStatusEnumApi } from '../generated/api.schemas'
import { cloudAgentsWebhooksLogic } from '../logics/cloudAgentsWebhooksLogic'
import { LoadErrorBanner } from './LoadErrorBanner'

const DELIVERY_STATUS_DISPLAY: Record<WebhookDeliveryStatusEnumApi, { label: string; type: LemonTagType }> = {
    [WebhookDeliveryStatusEnumApi.Pending]: { label: 'Pending', type: 'default' },
    [WebhookDeliveryStatusEnumApi.Succeeded]: { label: 'Delivered', type: 'success' },
    [WebhookDeliveryStatusEnumApi.Failed]: { label: 'Failed, will retry', type: 'warning' },
    [WebhookDeliveryStatusEnumApi.GaveUp]: { label: 'Gave up', type: 'danger' },
}

export function WebhookDeliveriesTable(): JSX.Element {
    const { deliveries, deliveriesLoading, deliveriesLoadFailed } = useValues(cloudAgentsWebhooksLogic)
    const { loadDeliveries } = useActions(cloudAgentsWebhooksLogic)

    const columns: LemonTableColumns<WebhookDeliveryApi> = [
        {
            title: 'Event',
            key: 'event',
            render: (_, delivery) => (
                <div className="flex flex-col" translate="no">
                    <span>{delivery.event_type}</span>
                    <span className="text-secondary text-xs break-all">{delivery.url}</span>
                </div>
            ),
        },
        {
            title: 'Status',
            key: 'status',
            render: (_, delivery) => {
                const display = DELIVERY_STATUS_DISPLAY[delivery.status] ?? { label: delivery.status, type: 'default' }
                return <LemonTag type={display.type}>{display.label}</LemonTag>
            },
        },
        { title: 'Attempts', key: 'attempts', align: 'right', render: (_, delivery) => delivery.attempts },
        {
            title: 'Last status code',
            key: 'last_status_code',
            align: 'right',
            render: (_, delivery) => delivery.last_status_code ?? <span className="text-secondary">None</span>,
        },
        { title: 'Time', key: 'created_at', render: (_, delivery) => <TZLabel time={delivery.created_at} /> },
    ]

    return (
        <div className="flex min-w-0 flex-col gap-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="m-0 text-base font-semibold">Recent deliveries</h3>
                <LemonButton
                    size="small"
                    type="secondary"
                    icon={<IconRefresh />}
                    loading={deliveriesLoading}
                    disabledReason={deliveriesLoading ? 'Loading the deliveries' : undefined}
                    onClick={loadDeliveries}
                    data-attr="cloud-agents-webhook-deliveries-refresh"
                >
                    Refresh
                </LemonButton>
            </div>
            {deliveries === null && deliveriesLoadFailed ? (
                <LoadErrorBanner what="the deliveries" onRetry={loadDeliveries} retrying={deliveriesLoading} />
            ) : (
                <LemonTable
                    size="small"
                    dataSource={deliveries ?? []}
                    columns={columns}
                    rowKey="id"
                    loading={deliveriesLoading}
                    emptyState="No deliveries yet. Send a test event to see one here."
                    data-attr="cloud-agents-webhook-deliveries"
                />
            )}
        </div>
    )
}
