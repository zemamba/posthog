import { LemonCard } from '@posthog/lemon-ui'

import { TZLabel } from 'lib/components/TZLabel'
import { dayjs } from 'lib/dayjs'
import { humanFriendlyDuration } from 'lib/utils/durations'

import type { CloudAgentAgentSessionApi } from '../generated/api.schemas'
import { RunStatusTag } from './RunStatusTag'

function sessionDuration(session: CloudAgentAgentSessionApi): string | null {
    if (!session.started_at || !session.ended_at) {
        return null
    }
    return humanFriendlyDuration(dayjs(session.ended_at).diff(dayjs(session.started_at), 'second'))
}

/** The agent sessions of a run. The first prompt starts session 1, and each message that resumes a stopped run starts one more. */
export function RunSessionsCard({ sessions }: { sessions: CloudAgentAgentSessionApi[] }): JSX.Element {
    return (
        <LemonCard hoverEffect={false} className="flex flex-col gap-3 p-4" data-attr="cloud-agents-run-sessions">
            <div>
                <h3 className="m-0 text-base font-semibold">Agent sessions</h3>
                <p className="m-0 text-secondary text-xs">
                    Each message that resumes a stopped run starts a new session on the same branch.
                </p>
            </div>
            {sessions.length === 0 ? (
                <p className="m-0 text-secondary">The first session starts when the sandbox is ready.</p>
            ) : (
                <ul className="m-0 flex list-none flex-col gap-2 p-0">
                    {sessions.map((session) => {
                        const duration = sessionDuration(session)
                        return (
                            <li key={session.index} className="flex flex-wrap items-center justify-between gap-2">
                                <div className="flex items-center gap-2">
                                    <span className="font-medium">Session {session.index + 1}</span>
                                    <RunStatusTag status={session.status} />
                                </div>
                                <div className="text-secondary text-xs">
                                    {session.started_at ? <TZLabel time={session.started_at} /> : 'Not started'}
                                    {duration && <span translate="no"> · {duration}</span>}
                                </div>
                            </li>
                        )
                    })}
                </ul>
            )}
        </LemonCard>
    )
}
