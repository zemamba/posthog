import { useActions, useValues } from 'kea'

import { IconTrash } from '@posthog/icons'
import { LemonButton, LemonDialog, LemonTable, LemonTableColumns, Link } from '@posthog/lemon-ui'

import { TZLabel } from 'lib/components/TZLabel'
import { urls } from 'scenes/urls'

import type { ProfileApi } from '../generated/api.schemas'
import { cloudAgentProfilesLogic } from '../logics/cloudAgentProfilesLogic'
import { cloudAgentsCatalogLogic } from '../logics/cloudAgentsCatalogLogic'
import { formatBoxSize, formatRate } from '../utils/pricing'
import { INFERENCE_MODE_DISPLAY } from '../utils/runStatus'

export function ProfilesTable(): JSX.Element {
    const { profiles, profilesLoading, deletingProfileId } = useValues(cloudAgentProfilesLogic)
    const { deleteProfile } = useActions(cloudAgentProfilesLogic)
    const { sizes } = useValues(cloudAgentsCatalogLogic)

    const columns: LemonTableColumns<ProfileApi> = [
        {
            title: 'Name',
            key: 'name',
            render: (_, profile) => (
                <div className="flex flex-col">
                    <Link
                        to={urls.cloudAgentProfile(profile.id)}
                        className="font-semibold"
                        data-attr="cloud-agents-profile-link"
                    >
                        {profile.name}
                    </Link>
                    {profile.description && (
                        <span className="text-secondary text-xs line-clamp-1 max-w-100">{profile.description}</span>
                    )}
                </div>
            ),
        },
        {
            title: 'Repository',
            key: 'repository',
            render: (_, profile) =>
                profile.repository ? (
                    <span className="whitespace-nowrap" translate="no">
                        {profile.repository}
                    </span>
                ) : (
                    <span className="text-secondary">Team default</span>
                ),
        },
        {
            title: 'Box size',
            key: 'size',
            render: (_, profile) => {
                const size = sizes.find((candidate) => candidate.name === profile.size)
                return size ? (
                    <div className="flex flex-col whitespace-nowrap" translate="no">
                        <span>{formatBoxSize(size)}</span>
                        <span className="text-secondary text-xs">{formatRate(size.price_per_hour_usd)} per hour</span>
                    </div>
                ) : (
                    <span className="text-secondary">Team default</span>
                )
            },
        },
        {
            title: 'Model provider',
            key: 'inference',
            render: (_, profile) =>
                profile.inference ? (
                    <span className="whitespace-nowrap">{INFERENCE_MODE_DISPLAY[profile.inference]?.label}</span>
                ) : (
                    <span className="text-secondary">Team default</span>
                ),
        },
        {
            title: 'Updated',
            key: 'updated_at',
            render: (_, profile) => <TZLabel time={profile.updated_at} />,
        },
        {
            key: 'actions',
            width: 0,
            render: (_, profile) => (
                <LemonButton
                    size="small"
                    status="danger"
                    icon={<IconTrash />}
                    tooltip="Delete profile"
                    loading={deletingProfileId === profile.id}
                    disabledReason={deletingProfileId ? 'Deleting a profile' : undefined}
                    onClick={() =>
                        LemonDialog.open({
                            title: `Delete the profile "${profile.name}"?`,
                            description:
                                'API calls that name this profile stop working. Runs that used it stay in the list.',
                            primaryButton: {
                                children: 'Delete profile',
                                status: 'danger',
                                onClick: () => deleteProfile(profile),
                                'data-attr': 'cloud-agents-profile-delete-confirm',
                            },
                            secondaryButton: { children: 'Cancel' },
                        })
                    }
                    data-attr="cloud-agents-profile-delete"
                />
            ),
        },
    ]

    return (
        <LemonTable
            dataSource={profiles ?? []}
            columns={columns}
            rowKey="id"
            loading={profilesLoading}
            emptyState={
                <div className="flex flex-col items-center gap-2 py-6 text-center">
                    <span className="font-semibold">No profiles yet</span>
                    <span className="text-secondary max-w-120">
                        A profile saves a repository, a box size and instructions under one name. Then an API call needs
                        only the profile name and a prompt.
                    </span>
                    <LemonButton
                        type="primary"
                        to={urls.cloudAgentProfile('new')}
                        data-attr="cloud-agents-profile-empty-new"
                    >
                        Create a profile
                    </LemonButton>
                </div>
            }
            data-attr="cloud-agents-profiles-table"
        />
    )
}
