import type { ReactNode } from 'react'

import { IconCheckCircle, IconInfo } from '@posthog/icons'
import { LemonButton, LemonCard, LemonCollapse, LemonTag, Spinner } from '@posthog/lemon-ui'

import { urls } from 'scenes/urls'
import type { Suggestion } from 'scenes/web-analytics/tabs/marketing-analytics/frontend/logic/setupPlanLogic'

import { SourceIcon } from 'products/data_warehouse/frontend/shared/components/SourceIcon'

export interface SourceSetupPanelProps {
    state: 'checking' | 'scanning' | 'suggestions' | 'empty' | 'error' | 'waiting'
    suggestions?: Suggestion[]
    connections?: {
        id: string
        name: string
        sourceType: string
        status: 'Connected' | 'Syncing' | 'Needs attention'
        detail: string
    }[]
    footer?: ReactNode
    onRetry?: () => void
    onDismiss?: (id: string) => void
}

export function SourceSetupPanel({
    state,
    suggestions = [],
    connections = [],
    footer,
    onRetry,
    onDismiss,
}: SourceSetupPanelProps): JSX.Element {
    const busy = state === 'checking' || state === 'scanning'
    const title =
        state === 'checking'
            ? 'Checking your connections'
            : state === 'scanning'
              ? 'Finding your ad platforms'
              : state === 'empty'
                ? 'Choose an ad platform'
                : state === 'error'
                  ? 'Could not check your events'
                  : state === 'waiting'
                    ? 'Your connections are getting ready'
                    : 'Connect your ad platforms'
    const description =
        state === 'checking'
            ? 'Looking for connected ad platforms.'
            : state === 'scanning'
              ? 'Checking campaign tracking in events from the last 7 days.'
              : state === 'empty'
                ? 'No ad platforms were detected in your recent events. Choose an integration to start importing spend data.'
                : state === 'error'
                  ? 'Try checking your events again, or choose an integration manually.'
                  : state === 'waiting'
                    ? 'Spend and ad performance will appear after the first sync finishes. You can connect other platforms while you wait.'
                    : `We found campaign tracking from ${suggestions.length} ${suggestions.length === 1 ? 'platform' : 'platforms'} in your recent events.`

    return (
        <LemonCard hoverEffect={false} className="max-w-3xl w-full mt-6 !p-0 overflow-hidden">
            <div className="p-6 space-y-5">
                <div className="flex items-center justify-between flex-wrap gap-2">
                    <span className="text-secondary text-xs font-semibold">Marketing sources</span>
                    {state === 'scanning' || state === 'suggestions' ? (
                        <LemonTag type="muted">Last 7 days</LemonTag>
                    ) : null}
                </div>
                <div className="flex items-start gap-3" role={busy ? 'status' : undefined}>
                    {busy ? <Spinner className="mt-1 shrink-0" /> : null}
                    <div className="min-w-0">
                        <h2 className="text-xl mb-2">{title}</h2>
                        <p className="text-secondary mb-0 max-w-xl">{description}</p>
                    </div>
                </div>
                {connections.length > 0 && (
                    <div className="divide-y border-t">
                        {connections.map((connection) => (
                            <div key={connection.id} className="py-4 space-y-2">
                                <div className="flex items-center flex-wrap gap-3">
                                    <SourceIcon type={connection.sourceType} size="small" disableTooltip />
                                    <strong>{connection.name}</strong>
                                    <LemonTag type={connection.status === 'Needs attention' ? 'warning' : 'info'}>
                                        {connection.status}
                                    </LemonTag>
                                </div>
                                <p className="text-secondary text-sm mb-0">{connection.detail}</p>
                            </div>
                        ))}
                    </div>
                )}
                {suggestions.length > 0 && !busy && (
                    <div className="divide-y border-t">
                        {suggestions.map((suggestion) => (
                            <div key={suggestion.id} className="py-4">
                                <div className="flex items-center justify-between flex-wrap gap-3">
                                    <div className="flex items-center gap-3 min-w-0">
                                        <SourceIcon
                                            type={suggestion.apply?.kind as string}
                                            size="small"
                                            disableTooltip
                                        />
                                        <div>
                                            <strong>{suggestion.title.replace(/^Connect /, '')}</strong>
                                            <p className="text-secondary text-sm mb-0">
                                                {suggestion.event_volume
                                                    ? `Found in ${suggestion.event_volume} events`
                                                    : 'Found in campaign tracking'}
                                            </p>
                                        </div>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <LemonButton
                                            type="primary"
                                            size="small"
                                            to={urls.dataWarehouseSourceNew(
                                                suggestion.apply?.kind as string,
                                                urls.marketingAnalyticsApp(),
                                                'Marketing analytics'
                                            )}
                                            targetBlank
                                            data-attr="marketing-onboarding-connect-source"
                                        >
                                            Connect
                                        </LemonButton>
                                        {onDismiss && (
                                            <LemonButton
                                                size="small"
                                                type="tertiary"
                                                onClick={() => onDismiss(suggestion.id)}
                                            >
                                                Dismiss
                                            </LemonButton>
                                        )}
                                    </div>
                                </div>
                                <LemonCollapse
                                    embedded
                                    size="small"
                                    className="mt-2"
                                    panels={[
                                        {
                                            key: suggestion.id,
                                            header: 'View detection details',
                                            content: (
                                                <p className="text-secondary text-sm mb-0">{suggestion.evidence}</p>
                                            ),
                                        },
                                    ]}
                                />
                            </div>
                        ))}
                    </div>
                )}
                {state === 'error' && onRetry && (
                    <LemonButton type="primary" onClick={onRetry} data-attr="marketing-onboarding-rescan">
                        Try again
                    </LemonButton>
                )}
                {!busy && state !== 'error' && state !== 'waiting' && (
                    <div className="flex items-start gap-2 text-secondary text-sm">
                        <IconInfo className="shrink-0 mt-0.5" />
                        <span>Spend data appears after the first sync finishes.</span>
                    </div>
                )}
                {state === 'waiting' && (
                    <div className="flex items-start gap-2 text-secondary text-sm">
                        <IconCheckCircle className="shrink-0 mt-0.5" />
                        <span>You can leave this page. Your import will continue in the background.</span>
                    </div>
                )}
            </div>
            {footer && (
                <div className="border-t p-4 flex flex-wrap items-center justify-between gap-3 bg-bg-light">
                    {footer}
                </div>
            )}
        </LemonCard>
    )
}
