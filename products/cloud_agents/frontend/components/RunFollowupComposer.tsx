import { useActions, useValues } from 'kea'

import { LemonBanner, LemonButton, LemonCard, LemonTextArea } from '@posthog/lemon-ui'

import { cloudAgentRunLogic } from '../logics/cloudAgentRunLogic'

export function RunFollowupComposer(): JSX.Element {
    const { followupText, followupSending, followupError, isActive } = useValues(cloudAgentRunLogic)
    const { setFollowupText, sendFollowup } = useActions(cloudAgentRunLogic)

    return (
        <LemonCard hoverEffect={false} className="flex flex-col gap-2 p-4" data-attr="cloud-agents-run-followup">
            <h3 className="m-0 text-base font-semibold">Send a message</h3>
            <p className="m-0 text-secondary text-xs">
                {isActive
                    ? 'The agent gets your message in its current session.'
                    : 'This run stopped. A message resumes it in a new session on the same branch, and the new session adds to the cost.'}
            </p>
            {followupError && <LemonBanner type="error">{followupError}</LemonBanner>}
            <LemonTextArea
                value={followupText}
                onChange={setFollowupText}
                onPressCmdEnter={sendFollowup}
                placeholder="Ask for a change, or tell the agent what to do next"
                minRows={3}
                disabled={followupSending}
                data-attr="cloud-agents-run-followup-input"
            />
            <LemonButton
                type="primary"
                className="self-end"
                onClick={sendFollowup}
                loading={followupSending}
                disabledReason={
                    followupSending
                        ? 'Sending your message'
                        : !followupText.trim()
                          ? 'Write a message first'
                          : undefined
                }
                data-attr="cloud-agents-run-followup-send"
            >
                {isActive ? 'Send' : 'Send and resume'}
            </LemonButton>
        </LemonCard>
    )
}
