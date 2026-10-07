import { LemonBanner, LemonCard, Link } from '@posthog/lemon-ui'

import { TZLabel } from 'lib/components/TZLabel'
import { LemonMarkdown } from 'lib/lemon-ui/LemonMarkdown'
import { urls } from 'scenes/urls'

import type { CloudAgentRunApi } from '../generated/api.schemas'
import { CloudAgentRunStatusEnumApi } from '../generated/api.schemas'
import { INFERENCE_MODE_DISPLAY, STOP_REASON_MESSAGES } from '../utils/runStatus'
import { RunStatusTag } from './RunStatusTag'

function Fact({ label, children }: { label: string; children: React.ReactNode }): JSX.Element {
    return (
        <div className="flex min-w-0 flex-col">
            <dt className="text-secondary text-xs font-normal">{label}</dt>
            <dd className="m-0 break-words">{children}</dd>
        </div>
    )
}

/** The status of a run, why it stopped, the prompt, and the facts about how it ran. */
export function RunSummaryCard({ run }: { run: CloudAgentRunApi }): JSX.Element {
    const failed = run.status === CloudAgentRunStatusEnumApi.Failed
    const stopMessage = run.stop_reason ? STOP_REASON_MESSAGES[run.stop_reason] : null

    return (
        <LemonCard hoverEffect={false} className="flex flex-col gap-3 p-4" data-attr="cloud-agents-run-summary">
            <div className="flex flex-wrap items-center gap-2">
                <RunStatusTag status={run.status} />
                {stopMessage && !failed && <span className="text-secondary">{stopMessage}</span>}
            </div>
            {failed && (
                <LemonBanner type="error">
                    {run.error || stopMessage || 'The run failed.'} Send a message below to try again on the same
                    branch.
                </LemonBanner>
            )}
            <div>
                <div className="text-secondary text-xs">Prompt</div>
                <p className="m-0 whitespace-pre-wrap break-words" translate="no">
                    {run.prompt}
                </p>
            </div>
            {run.result.summary && (
                <div>
                    <div className="text-secondary text-xs">Result</div>
                    <div className="break-words" translate="no">
                        <LemonMarkdown lowKeyHeadings disableImages="all">
                            {run.result.summary}
                        </LemonMarkdown>
                    </div>
                </div>
            )}
            <dl className="m-0 grid grid-cols-2 gap-3 border-t pt-3 @min-[40rem]/main-content:grid-cols-4">
                <Fact label="Repository">
                    <span translate="no">{run.repository}</span>
                </Fact>
                <Fact label="Branch">
                    <span translate="no">{run.branch ?? 'Default branch'}</span>
                </Fact>
                <Fact label="Profile">
                    {run.profile ? <Link to={urls.cloudAgentProfile(run.profile.id)}>{run.profile.name}</Link> : 'None'}
                </Fact>
                <Fact label="Model">
                    <span translate="no">{run.config.model ?? 'Default'}</span>
                </Fact>
                <Fact label="Model provider">{INFERENCE_MODE_DISPLAY[run.config.inference]?.label}</Fact>
                <Fact label="Started by">
                    <span translate="no">{run.created_by?.email ?? (run.caller === 'api' ? 'API' : 'Unknown')}</span>
                </Fact>
                <Fact label="Created">
                    <TZLabel time={run.created_at} />
                </Fact>
                <Fact label="Finished">{run.completed_at ? <TZLabel time={run.completed_at} /> : 'Not finished'}</Fact>
            </dl>
        </LemonCard>
    )
}
