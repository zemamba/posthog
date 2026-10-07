import { useActions, useValues } from 'kea'
import { Form } from 'kea-forms'

import { LemonButton, LemonInput, LemonInputSelect, LemonSkeleton, LemonTextArea } from '@posthog/lemon-ui'

import { NotFound } from 'lib/components/NotFound'
import { useFeatureFlag } from 'lib/hooks/useFeatureFlag'
import { LemonField } from 'lib/lemon-ui/LemonField'
import { SceneExport } from 'scenes/sceneTypes'
import { urls } from 'scenes/urls'

import { SceneContent } from '~/layout/scenes/components/SceneContent'
import { SceneTitleSection } from '~/layout/scenes/components/SceneTitleSection'
import { ProductKey } from '~/queries/schema/schema-general'

import { BoxCostLine } from '../components/BoxCostLine'
import { BoxSizeSelect } from '../components/BoxSizeSelect'
import { InferenceModeSelect } from '../components/InferenceModeSelect'
import { LoadErrorBanner } from '../components/LoadErrorBanner'
import { ModelSelect } from '../components/ModelSelect'
import { ProfileApiSnippet } from '../components/ProfileApiSnippet'
import { CloudAgentProfileLogicProps, cloudAgentProfileLogic } from '../logics/cloudAgentProfileLogic'
import { COST_EXAMPLE_MINUTES } from '../logics/cloudAgentsNewRunLogic'

export const scene: SceneExport<CloudAgentProfileLogicProps> = {
    component: CloudAgentProfileScene,
    logic: cloudAgentProfileLogic,
    paramsToProps: ({ params: { id } }) => ({ id }),
    productKey: ProductKey.CLOUD_AGENTS,
}

export function CloudAgentProfileScene({ id }: CloudAgentProfileLogicProps): JSX.Element {
    const enabled = useFeatureFlag('CLOUD_AGENTS')
    const logic = cloudAgentProfileLogic({ id })
    const { isNew, profile, profileLoading, profileLoadError, profileForm, isProfileFormSubmitting } = useValues(logic)
    const { loadProfile, submitProfileForm } = useActions(logic)

    if (!enabled || profileLoadError === 'not_found') {
        return <NotFound object="profile" caption="Check the link, or open the list of profiles to find it." />
    }

    const waitingForProfile = !isNew && profile === null

    return (
        <SceneContent>
            <SceneTitleSection
                name={isNew ? 'New profile' : (profile?.name ?? 'Profile')}
                description="A profile is a saved setup for runs. The API can start a run from it with only a prompt."
                resourceType={{ type: 'cloud_agent' }}
                forceBackTo={{ key: 'cloud-agent-profiles', name: 'Profiles', path: urls.cloudAgentProfiles() }}
                actions={
                    <>
                        <LemonButton
                            type="secondary"
                            size="small"
                            to={urls.cloudAgentProfiles()}
                            data-attr="cloud-agents-profile-cancel"
                        >
                            Cancel
                        </LemonButton>
                        <LemonButton
                            type="primary"
                            size="small"
                            onClick={submitProfileForm}
                            loading={isProfileFormSubmitting}
                            disabledReason={
                                isProfileFormSubmitting
                                    ? 'Saving the profile'
                                    : waitingForProfile
                                      ? 'The profile is not loaded yet'
                                      : undefined
                            }
                            data-attr="cloud-agents-profile-save"
                        >
                            Save profile
                        </LemonButton>
                    </>
                }
            />
            {waitingForProfile && profileLoadError === 'failed' ? (
                <LoadErrorBanner what="this profile" onRetry={loadProfile} retrying={profileLoading} />
            ) : waitingForProfile ? (
                <div className="flex flex-col gap-3">
                    <LemonSkeleton className="h-10" />
                    <LemonSkeleton className="h-48" />
                </div>
            ) : (
                <div className="grid grid-cols-1 items-start gap-4 @min-[56rem]/main-content:grid-cols-3">
                    <Form
                        logic={cloudAgentProfileLogic}
                        props={{ id }}
                        formKey="profileForm"
                        enableFormOnSubmit
                        className="flex min-w-0 flex-col gap-3 @min-[56rem]/main-content:col-span-2"
                    >
                        <LemonField name="name" label="Name" help="API calls use this name to pick the profile.">
                            <LemonInput
                                placeholder="nightly-dependency-updates"
                                data-attr="cloud-agents-profile-name"
                            />
                        </LemonField>
                        <LemonField name="description" label="Description" showOptional>
                            <LemonInput placeholder="What this profile is for" />
                        </LemonField>
                        <div className="grid grid-cols-1 gap-3 @min-[40rem]/main-content:grid-cols-2">
                            <LemonField name="repository" label="Repository" showOptional>
                                <LemonInput placeholder="owner/name" data-attr="cloud-agents-profile-repository" />
                            </LemonField>
                            <LemonField name="branch" label="Branch" showOptional>
                                <LemonInput placeholder="The default branch" />
                            </LemonField>
                        </div>
                        <LemonField name="size" label="Box size">
                            {({ value, onChange }) => (
                                <div className="flex flex-col gap-1">
                                    <BoxSizeSelect
                                        value={value}
                                        onChange={onChange}
                                        emptyLabel="Team default"
                                        data-attr="cloud-agents-profile-size"
                                    />
                                    <BoxCostLine
                                        sizeName={value}
                                        minutes={COST_EXAMPLE_MINUTES}
                                        fallback="Runs use the box size from the team defaults."
                                    />
                                </div>
                            )}
                        </LemonField>
                        <div className="grid grid-cols-1 gap-3 @min-[40rem]/main-content:grid-cols-2">
                            <LemonField name="model" label="Model">
                                {({ value, onChange }) => <ModelSelect value={value} onChange={onChange} />}
                            </LemonField>
                            <LemonField name="inference" label="Model provider">
                                {({ value, onChange }) => (
                                    <InferenceModeSelect value={value} onChange={onChange} emptyLabel="Team default" />
                                )}
                            </LemonField>
                        </div>
                        <LemonField
                            name="instructions"
                            label="Instructions"
                            showOptional
                            help="The agent gets these with each prompt, for example your coding standards or how to run the tests."
                        >
                            <LemonTextArea minRows={4} placeholder="Run pnpm test before you open the pull request." />
                        </LemonField>
                        <LemonField
                            name="tags"
                            label="Tags"
                            showOptional
                            help="Each run from this profile gets these tags."
                        >
                            <LemonInputSelect mode="multiple" allowCustomValues placeholder="Add a tag" />
                        </LemonField>
                    </Form>
                    <ProfileApiSnippet profileName={profileForm.name} />
                </div>
            )}
        </SceneContent>
    )
}
