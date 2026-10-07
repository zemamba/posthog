import { useActions, useValues } from 'kea'

import { LemonBanner, LemonButton, LemonDialog, LemonSkeleton } from '@posthog/lemon-ui'

import { CopyToClipboardInline } from 'lib/components/CopyToClipboard'

import { cloudAgentsSettingsLogic } from '../logics/cloudAgentsSettingsLogic'
import { cloudAgentsWebhooksLogic } from '../logics/cloudAgentsWebhooksLogic'

/** The signing secret of the project. The API returns it one time, so the copy step happens here. */
export function WebhookSigningSecret(): JSX.Element {
    const { settings } = useValues(cloudAgentsSettingsLogic)
    const { revealedSecret, secretRequestInFlight } = useValues(cloudAgentsWebhooksLogic)
    const { createSecret, rotateSecret, dismissSecret } = useActions(cloudAgentsWebhooksLogic)

    if (settings === null) {
        return <LemonSkeleton className="h-10 max-w-180" />
    }
    return (
        <div className="flex max-w-180 flex-col gap-2" data-attr="cloud-agents-webhook-secret">
            <h3 className="m-0 text-base font-semibold">Signing secret</h3>
            {revealedSecret && (
                <LemonBanner type="success" onClose={dismissSecret}>
                    <div className="flex min-w-0 flex-col gap-1">
                        <span>Copy the secret now. You cannot see it again after you close this message.</span>
                        <CopyToClipboardInline
                            description="signing secret"
                            isValueSensitive
                            className="font-mono break-all"
                        >
                            {revealedSecret}
                        </CopyToClipboardInline>
                    </div>
                </LemonBanner>
            )}
            <div className="flex flex-wrap items-center gap-2">
                <span className="text-secondary">
                    {settings.webhook_secret_set
                        ? 'This project has a signing secret. PostHog signs each event with it.'
                        : 'This project has no signing secret yet. Create one so that your server can check each event.'}
                </span>
                {settings.webhook_secret_set ? (
                    <LemonButton
                        type="secondary"
                        size="small"
                        loading={secretRequestInFlight}
                        disabledReason={secretRequestInFlight ? 'Rotating the secret' : undefined}
                        onClick={() =>
                            LemonDialog.open({
                                title: 'Rotate the signing secret?',
                                description:
                                    'The old secret stops working at once. Events fail your signature check until your server uses the new secret.',
                                primaryButton: { children: 'Rotate secret', status: 'danger', onClick: rotateSecret },
                                secondaryButton: { children: 'Cancel' },
                            })
                        }
                        data-attr="cloud-agents-webhook-secret-rotate"
                    >
                        Rotate secret
                    </LemonButton>
                ) : (
                    <LemonButton
                        type="primary"
                        size="small"
                        loading={secretRequestInFlight}
                        disabledReason={secretRequestInFlight ? 'Creating the secret' : undefined}
                        onClick={createSecret}
                        data-attr="cloud-agents-webhook-secret-create"
                    >
                        Create secret
                    </LemonButton>
                )}
            </div>
        </div>
    )
}
