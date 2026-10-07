import { LemonTag } from '@posthog/lemon-ui'

import type { CloudAgentRunStatusEnumApi } from '../generated/api.schemas'
import { RUN_STATUS_DISPLAY } from '../utils/runStatus'

export function RunStatusTag({ status }: { status: CloudAgentRunStatusEnumApi }): JSX.Element {
    const display = RUN_STATUS_DISPLAY[status] ?? { label: status, type: 'default' as const }
    return <LemonTag type={display.type}>{display.label}</LemonTag>
}
