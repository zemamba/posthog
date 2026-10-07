import { useActions, useValues } from 'kea'

import { LemonButton, LemonDialog, LemonInput, LemonTag } from '@posthog/lemon-ui'

import { TZLabel } from 'lib/components/TZLabel'

import type { InferenceCredentialKindEnumApi } from '~/generated/core/api.schemas'

import { inferenceCredentialsLogic } from '../logics/inferenceCredentialsLogic'

export interface ModelProviderKind {
    kind: InferenceCredentialKindEnumApi
    name: string
    hint: string
    placeholder: string
}

/** One credential kind: its connected state, and the controls to connect, replace or remove it. */
export function ModelProviderRow({ provider }: { provider: ModelProviderKind }): JSX.Element {
    const { credentialsByKind, secrets, connecting, connectErrors, removing } = useValues(inferenceCredentialsLogic)
    const { setSecret, connectCredential, removeCredential } = useActions(inferenceCredentialsLogic)
    const { kind } = provider
    const credential = credentialsByKind[kind]
    const isConnecting = !!connecting[kind]
    const isRemoving = !!removing[kind]

    return (
        <div className="flex min-w-0 flex-col gap-2 rounded border p-3" data-attr={`cloud-agents-provider-${kind}`}>
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex flex-wrap items-center gap-2">
                    <span className="font-semibold">{provider.name}</span>
                    {credential ? (
                        <LemonTag type="success">Connected</LemonTag>
                    ) : (
                        <LemonTag type="muted">Not connected</LemonTag>
                    )}
                </div>
                {credential && (
                    <LemonButton
                        size="small"
                        status="danger"
                        type="secondary"
                        loading={isRemoving}
                        disabledReason={isRemoving ? 'Removing the credential' : undefined}
                        onClick={() =>
                            LemonDialog.open({
                                title: `Remove your ${provider.name}?`,
                                description:
                                    'Runs that ask for this credential fail until you connect it again. Runs on the automatic option use the next one in the order.',
                                primaryButton: {
                                    children: 'Remove',
                                    status: 'danger',
                                    onClick: () => removeCredential(kind),
                                },
                                secondaryButton: { children: 'Cancel' },
                            })
                        }
                        data-attr="cloud-agents-credential-remove"
                    >
                        Remove
                    </LemonButton>
                )}
            </div>
            {credential && (
                <div className="text-secondary flex flex-wrap gap-x-4 gap-y-1 text-xs">
                    <span translate="no">••••{credential.key_suffix}</span>
                    <span>
                        {credential.last_used_at ? (
                            <>
                                Last used <TZLabel time={credential.last_used_at} />
                            </>
                        ) : (
                            'Not used yet'
                        )}
                    </span>
                </div>
            )}
            <div className="flex flex-wrap items-start gap-2">
                <LemonInput
                    type="password"
                    className="min-w-48 flex-1 ph-no-capture"
                    placeholder={provider.placeholder}
                    value={secrets[kind] ?? ''}
                    onChange={(secret) => setSecret(kind, secret)}
                    onPressEnter={() => connectCredential(kind)}
                    disabled={isConnecting}
                    status={connectErrors[kind] ? 'danger' : undefined}
                    autoComplete="off"
                    data-attr="cloud-agents-credential-secret"
                />
                <LemonButton
                    type={credential ? 'secondary' : 'primary'}
                    loading={isConnecting}
                    disabledReason={isConnecting ? 'Checking the key' : undefined}
                    onClick={() => connectCredential(kind)}
                    data-attr="cloud-agents-credential-connect"
                >
                    {credential ? 'Replace' : 'Connect'}
                </LemonButton>
            </div>
            {connectErrors[kind] ? (
                <span className="text-danger text-xs">{connectErrors[kind]}</span>
            ) : (
                <span className="text-secondary text-xs">{provider.hint}</span>
            )}
        </div>
    )
}
