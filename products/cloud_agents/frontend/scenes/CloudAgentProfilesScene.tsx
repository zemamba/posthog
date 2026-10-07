import { useActions, useValues } from 'kea'

import { IconPlusSmall } from '@posthog/icons'
import { LemonButton } from '@posthog/lemon-ui'

import { SceneExport } from 'scenes/sceneTypes'
import { urls } from 'scenes/urls'

import { ProductKey } from '~/queries/schema/schema-general'

import { CloudAgentsSceneShell } from '../components/CloudAgentsSceneShell'
import { LoadErrorBanner } from '../components/LoadErrorBanner'
import { ProfilesTable } from '../components/ProfilesTable'
import { cloudAgentProfilesLogic } from '../logics/cloudAgentProfilesLogic'
import { CloudAgentsSceneLogicProps, cloudAgentsSceneLogic } from '../logics/cloudAgentsSceneLogic'

export const scene: SceneExport<CloudAgentsSceneLogicProps> = {
    component: CloudAgentProfilesScene,
    logic: cloudAgentsSceneLogic,
    paramsToProps: () => ({ scene: 'profiles' }),
    productKey: ProductKey.CLOUD_AGENTS,
}

export function CloudAgentProfilesScene(): JSX.Element {
    const { profiles, profilesLoadFailed, profilesLoading } = useValues(cloudAgentProfilesLogic)
    const { loadProfiles } = useActions(cloudAgentProfilesLogic)

    return (
        <CloudAgentsSceneShell
            activeTab="profiles"
            actions={
                <LemonButton
                    type="primary"
                    size="small"
                    icon={<IconPlusSmall />}
                    to={urls.cloudAgentProfile('new')}
                    data-attr="cloud-agents-new-profile"
                >
                    New profile
                </LemonButton>
            }
        >
            {profiles === null && profilesLoadFailed ? (
                <LoadErrorBanner what="the profiles" onRetry={loadProfiles} retrying={profilesLoading} />
            ) : (
                <ProfilesTable />
            )}
        </CloudAgentsSceneShell>
    )
}
