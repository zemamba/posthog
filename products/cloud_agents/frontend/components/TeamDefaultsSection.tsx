import { useActions, useValues } from 'kea'
import { Form } from 'kea-forms'

import { LemonButton, LemonInput, LemonSelect, LemonSkeleton, LemonTextArea } from '@posthog/lemon-ui'

import { LemonField } from 'lib/lemon-ui/LemonField'

import { cloudAgentProfilesLogic } from '../logics/cloudAgentProfilesLogic'
import { COST_EXAMPLE_MINUTES } from '../logics/cloudAgentsNewRunLogic'
import { cloudAgentsSettingsLogic } from '../logics/cloudAgentsSettingsLogic'
import { BoxCostLine } from './BoxCostLine'
import { BoxSizeSelect } from './BoxSizeSelect'
import { InferenceModeSelect } from './InferenceModeSelect'
import { LoadErrorBanner } from './LoadErrorBanner'
import { ModelSelect } from './ModelSelect'
import { SettingsSection } from './SettingsSection'
import { TeamLimits } from './TeamLimits'

export function TeamDefaultsSection(): JSX.Element {
    const { settings, settingsLoading, settingsLoadFailed, isTeamDefaultsSubmitting, teamDefaultsChanged } =
        useValues(cloudAgentsSettingsLogic)
    const { loadSettings, submitTeamDefaults } = useActions(cloudAgentsSettingsLogic)
    const { profiles } = useValues(cloudAgentProfilesLogic)

    return (
        <SettingsSection
            title="Team defaults"
            description="A run uses these values when the request and its profile leave a field out."
            data-attr="cloud-agents-team-defaults"
        >
            {settings === null && settingsLoadFailed ? (
                <LoadErrorBanner what="the team defaults" onRetry={loadSettings} retrying={settingsLoading} />
            ) : settings === null ? (
                <LemonSkeleton className="h-48" />
            ) : (
                <Form
                    logic={cloudAgentsSettingsLogic}
                    formKey="teamDefaults"
                    enableFormOnSubmit
                    className="flex max-w-180 flex-col gap-3"
                >
                    <div className="grid grid-cols-1 gap-3 @min-[40rem]/main-content:grid-cols-2">
                        <LemonField name="repository" label="Repository" showOptional>
                            <LemonInput placeholder="owner/name" data-attr="cloud-agents-defaults-repository" />
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
                                    emptyLabel="PostHog default"
                                    data-attr="cloud-agents-defaults-size"
                                />
                                <BoxCostLine
                                    sizeName={value}
                                    minutes={COST_EXAMPLE_MINUTES}
                                    fallback="Choose a box size to see its price."
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
                                <InferenceModeSelect value={value} onChange={onChange} emptyLabel="PostHog default" />
                            )}
                        </LemonField>
                    </div>
                    <LemonField
                        name="default_profile"
                        label="Default profile"
                        showOptional
                        help="Runs that name no profile use this one."
                    >
                        {({ value, onChange }) => (
                            <LemonSelect
                                fullWidth
                                value={value}
                                onChange={onChange}
                                options={[
                                    { value: null, label: 'No default profile' },
                                    ...(profiles ?? []).map((profile) => ({
                                        value: profile.name,
                                        label: profile.name,
                                    })),
                                ]}
                                data-attr="cloud-agents-defaults-profile"
                            />
                        )}
                    </LemonField>
                    <LemonField
                        name="instructions"
                        label="Instructions"
                        showOptional
                        help="The agent gets these with each prompt in this project."
                    >
                        <LemonTextArea minRows={3} placeholder="Follow the conventions in CONTRIBUTING.md." />
                    </LemonField>
                    <TeamLimits />
                    <LemonButton
                        type="primary"
                        className="self-start"
                        onClick={submitTeamDefaults}
                        loading={isTeamDefaultsSubmitting}
                        disabledReason={
                            isTeamDefaultsSubmitting
                                ? 'Saving the team defaults'
                                : !teamDefaultsChanged
                                  ? 'No changes to save'
                                  : undefined
                        }
                        data-attr="cloud-agents-defaults-save"
                    >
                        Save defaults
                    </LemonButton>
                </Form>
            )}
        </SettingsSection>
    )
}
