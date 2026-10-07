/** The fields of a PostHog API error that the messages below read. `ApiError` has them all. */
interface ApiErrorLike {
    status?: number
    code?: string | null
    detail?: string | null
}

function asApiError(error: unknown): ApiErrorLike {
    return error && typeof error === 'object' ? (error as ApiErrorLike) : {}
}

const RUN_ERROR_MESSAGES: Record<string, string> = {
    usage_limited:
        'This project reached its usage limit, so the run did not start. Raise the limit in billing settings, then try again.',
    create_rate_limited: 'This project started too many runs in the last hour. Wait a few minutes, then try again.',
    concurrency_limited:
        'This project already has the maximum number of runs in progress. Wait for one to finish or cancel one, then try again.',
    repository_required: 'Choose a repository for the run, or set a default repository in settings.',
    credential_owner_required:
        'This run uses the model provider of the person who started it, so only that person can continue it. Start a new run to use your own provider.',
    run_stopping: 'This run is stopping. Wait until it stops, then send your message to resume it.',
    run_not_resumable: 'This run cannot be resumed. Start a new run from the same prompt.',
    cancel_unavailable: 'This run cannot be canceled right now. Refresh the page and try again.',
}

/** The message for a failed run request: a known error code first, then the API detail, then the fallback. */
export function describeRunError(error: unknown, fallback: string): string {
    const { code, detail } = asApiError(error)
    if (code && RUN_ERROR_MESSAGES[code]) {
        return RUN_ERROR_MESSAGES[code]
    }
    return detail || fallback
}

/** The message for a failed attempt to connect a model provider credential. */
export function describeCredentialError(error: unknown): string {
    const { status, detail } = asApiError(error)
    if (status === 400) {
        return detail || 'The provider did not accept this key. Check that you copied the whole key, then try again.'
    }
    if (status === 403) {
        return 'Your organization cannot connect this kind of credential yet. Use an API key, or ask PostHog support to turn it on.'
    }
    if (status === 502) {
        return 'We could not reach the provider to check this key. Wait a moment, then try again.'
    }
    return detail || 'We could not save this credential. Try again, and contact support if it keeps happening.'
}
