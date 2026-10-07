import { MakeLogicType, actions, afterMount, kea, key, path, props, reducers } from 'kea'

import { marketingAnalyticsLogic } from 'scenes/web-analytics/tabs/marketing-analytics/frontend/logic/marketingAnalyticsLogic'
import { setupPlanLogic } from 'scenes/web-analytics/tabs/marketing-analytics/frontend/logic/setupPlanLogic'

type DetectedSourcesProps = { teamId: number }

export const detectedSourcesLogic = kea<
    MakeLogicType<
        { notificationDismissed: boolean; dismissedSourceIds: string[] },
        {
            dismiss: () => { value: true }
            expand: () => { value: true }
            dismissSource: (id: string) => { id: string }
        },
        DetectedSourcesProps
    >
>([
    props({} as DetectedSourcesProps),
    key((props) => props.teamId),
    path((key) => ['products', 'marketingAnalytics', 'detectedSources', key]),
    actions({ dismiss: true, expand: true, dismissSource: (id: string) => ({ id }) }),
    reducers(({ props }) => ({
        dismissedSourceIds: [
            [] as string[],
            { persist: true, prefix: `${props.teamId}__` },
            { dismissSource: (state, { id }) => [...new Set([...state, id])] },
        ],
        notificationDismissed: [
            false,
            { persist: true, prefix: `${props.teamId}__` },
            { dismiss: () => true, expand: () => false },
        ],
    })),
    afterMount(({ props, cache }) => {
        if (props.teamId && !setupPlanLogic.values.setupPlan && !setupPlanLogic.values.setupPlanLoading) {
            setupPlanLogic.actions.loadSetupPlan()
        }
        cache.disposables.add(() => {
            const refreshSources = (): void => {
                if (!marketingAnalyticsLogic.values.loading) {
                    marketingAnalyticsLogic.actions.loadSources()
                }
            }
            window.addEventListener('focus', refreshSources)
            const interval = window.setInterval(() => {
                if (
                    marketingAnalyticsLogic.values.allAvailableSourcesWithStatus.some(
                        (source) => source.status === 'Running'
                    )
                ) {
                    refreshSources()
                }
            }, 30000)
            return () => {
                window.removeEventListener('focus', refreshSources)
                window.clearInterval(interval)
            }
        }, 'source-health')
    }),
])
