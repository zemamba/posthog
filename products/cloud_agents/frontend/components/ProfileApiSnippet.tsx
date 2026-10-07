import { LemonCard } from '@posthog/lemon-ui'

import { CurlSnippet } from './CurlSnippet'

/** How to start a run from this profile over the API: the profile name and a prompt are the whole request. */
export function ProfileApiSnippet({ profileName }: { profileName: string }): JSX.Element {
    return (
        <LemonCard hoverEffect={false} className="flex flex-col gap-2 p-4 min-w-0">
            <h3 className="m-0 text-base font-semibold">Trigger this profile from the API</h3>
            <p className="m-0 text-secondary text-xs">
                The profile supplies the repository, the box size and the instructions. The request needs only the
                profile name and a prompt.
            </p>
            <CurlSnippet
                surface="profile"
                body={{ profile: profileName.trim() || '<name>', prompt: 'Fix the failing checkout test' }}
            />
        </LemonCard>
    )
}
