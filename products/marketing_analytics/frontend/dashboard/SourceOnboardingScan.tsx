import { LemonButton, LemonCard, Spinner } from '@posthog/lemon-ui'

import { urls } from 'scenes/urls'
import type { Suggestion } from 'scenes/web-analytics/tabs/marketing-analytics/frontend/logic/setupPlanLogic'

import { SourceIcon } from 'products/data_warehouse/frontend/shared/components/SourceIcon'

export interface SourceOnboardingScanProps {
    loading: boolean
    failed: boolean
    suggestions: Suggestion[]
    onManual: () => void
    onContinue: () => void
    onRescan: () => void
}

export function SourceOnboardingScan({
    loading,
    failed,
    suggestions,
    onManual,
    onContinue,
    onRescan,
}: SourceOnboardingScanProps): JSX.Element {
    return (
        <LemonCard hoverEffect={false} className="space-y-4">
            {loading ? (
                <div role="status" className="flex items-center gap-3 py-8">
                    <Spinner />
                    <div>
                        <h3 className="mb-1">Scanning events from the last 7 days</h3>
                        <p className="text-secondary mb-0">
                            Looking for campaign tracking to suggest your marketing sources.
                        </p>
                    </div>
                </div>
            ) : failed ? (
                <div>
                    <h3>Could not scan your events</h3>
                    <p className="text-secondary">Try scanning again or add a source manually.</p>
                    <LemonButton onClick={onRescan} data-attr="marketing-onboarding-rescan">
                        Scan events again
                    </LemonButton>
                </div>
            ) : suggestions.length ? (
                <div>
                    <h3>Connect your detected marketing sources</h3>
                    <p className="text-secondary">
                        These platforms appear in your events from the last 7 days. You can connect other sources while
                        the first sync runs.
                    </p>
                    {suggestions.map((suggestion) => (
                        <div
                            key={suggestion.id}
                            className="flex flex-wrap items-center justify-between gap-4 py-3 border-t"
                        >
                            <div className="min-w-0">
                                <div className="flex items-center gap-2">
                                    <SourceIcon type={suggestion.apply?.kind as string} size="small" disableTooltip />
                                    <strong>{suggestion.title}</strong>
                                </div>
                                <p className="text-secondary text-sm mb-0 mt-2">{suggestion.evidence}</p>
                            </div>
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
                        </div>
                    ))}
                </div>
            ) : (
                <div>
                    <h3>No marketing sources detected</h3>
                    <p className="text-secondary mb-0">
                        No ad platforms were detected in your events from the last 7 days. You can add a source
                        manually.
                    </p>
                </div>
            )}
            <div className="flex flex-wrap justify-end gap-2 border-t pt-4">
                <LemonButton onClick={onManual} data-attr="marketing-onboarding-add-manually">
                    Skip and add manually
                </LemonButton>
                <LemonButton type="primary" onClick={onContinue} data-attr="marketing-onboarding-continue">
                    Continue to dashboard
                </LemonButton>
            </div>
        </LemonCard>
    )
}
