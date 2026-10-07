import { useActions, useValues } from 'kea'

import { LemonInput, LemonSelect } from '@posthog/lemon-ui'

import { CloudAgentRunStatusEnumApi } from '../generated/api.schemas'
import { cloudAgentProfilesLogic } from '../logics/cloudAgentProfilesLogic'
import { cloudAgentsRunsLogic } from '../logics/cloudAgentsRunsLogic'
import { RUN_STATUS_DISPLAY } from '../utils/runStatus'

export function RunsFilters(): JSX.Element {
    const { filters } = useValues(cloudAgentsRunsLogic)
    const { setFilters } = useActions(cloudAgentsRunsLogic)
    const { profiles, profilesLoading } = useValues(cloudAgentProfilesLogic)

    return (
        <div className="flex flex-wrap items-center gap-2">
            <LemonInput
                type="search"
                className="min-w-48 flex-1 @min-[40rem]/main-content:flex-none @min-[40rem]/main-content:w-64"
                placeholder="Search by repository"
                value={filters.repository}
                onChange={(repository) => setFilters({ repository })}
                data-attr="cloud-agents-runs-repository-filter"
            />
            <LemonSelect
                size="small"
                value={filters.status}
                onChange={(status) => setFilters({ status })}
                options={[
                    { value: null, label: 'Any status' },
                    ...Object.values(CloudAgentRunStatusEnumApi).map((status) => ({
                        value: status,
                        label: RUN_STATUS_DISPLAY[status].label,
                    })),
                ]}
                data-attr="cloud-agents-runs-status-filter"
            />
            <LemonSelect
                size="small"
                value={filters.profileId}
                onChange={(profileId) => setFilters({ profileId })}
                loading={profilesLoading}
                options={[
                    { value: null, label: 'Any profile' },
                    ...(profiles ?? []).map((profile) => ({ value: profile.id, label: profile.name })),
                ]}
                data-attr="cloud-agents-runs-profile-filter"
            />
        </div>
    )
}
