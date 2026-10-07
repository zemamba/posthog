import { apiMutator } from '../../../../frontend/src/lib/api-orval-mutator'
/**
 * Auto-generated from the Django backend OpenAPI schema.
 * To modify these types, update the Django serializers or views, then run:
 *   hogli build:openapi
 * Questions or issues? #team-devex on Slack
 *
 * PostHog API - generated
 * OpenAPI spec version: 1.0.0
 */
import type {
    CloudAgentCatalogApi,
    CloudAgentEstimateApi,
    CloudAgentRunApi,
    CloudAgentRunCreateApi,
    CloudAgentRunEventsApi,
    CloudAgentRunMessageApi,
    CloudAgentRunMessageResponseApi,
    CloudAgentRunUsageApi,
    CloudAgentSettingsApi,
    CloudAgentUsageSummaryApi,
    CloudAgentsEstimateRetrieveParams,
    CloudAgentsProfilesListParams,
    CloudAgentsRunsEventsRetrieveParams,
    CloudAgentsRunsListParams,
    CloudAgentsUsageRetrieveParams,
    CloudAgentsWebhookEndpointsListParams,
    PaginatedCloudAgentRunListApi,
    PaginatedProfileListApi,
    PaginatedWebhookEndpointListApi,
    PatchedCloudAgentSettingsUpdateApi,
    PatchedProfileUpdateApi,
    PatchedWebhookEndpointUpdateApi,
    ProfileApi,
    ProfileCreateApi,
    WebhookDeliveryApi,
    WebhookEndpointApi,
    WebhookEndpointCreateApi,
    WebhookSecretApi,
    WebhookTestApi,
} from './api.schemas'

export const getCloudAgentsCatalogRetrieveUrl = (projectId: string) => {
    return `/api/projects/${projectId}/cloud_agents/catalog/`
}

/**
 * The sizes, models and inference modes that a run can use, with the prices and the limits.
 * @summary Retrieve the cloud agents catalog
 */
export const cloudAgentsCatalogRetrieve = async (
    projectId: string,
    options?: RequestInit
): Promise<CloudAgentCatalogApi> => {
    return apiMutator<CloudAgentCatalogApi>(getCloudAgentsCatalogRetrieveUrl(projectId), {
        ...options,
        method: 'GET',
    })
}

export const getCloudAgentsEstimateRetrieveUrl = (projectId: string, params: CloudAgentsEstimateRetrieveParams) => {
    const normalizedParams = new URLSearchParams()

    Object.entries(params || {}).forEach(([key, value]) => {
        if (value !== undefined) {
            normalizedParams.append(key, value === null ? 'null' : String(value))
        }
    })

    const stringifiedParams = normalizedParams.toString()

    return stringifiedParams.length > 0
        ? `/api/projects/${projectId}/cloud_agents/estimate/?${stringifiedParams}`
        : `/api/projects/${projectId}/cloud_agents/estimate/`
}

/**
 * The compute cost of a sandbox of one size for a number of minutes. Model usage is not included.
 * @summary Estimate the compute cost of a run
 */
export const cloudAgentsEstimateRetrieve = async (
    projectId: string,
    params: CloudAgentsEstimateRetrieveParams,
    options?: RequestInit
): Promise<CloudAgentEstimateApi> => {
    return apiMutator<CloudAgentEstimateApi>(getCloudAgentsEstimateRetrieveUrl(projectId, params), {
        ...options,
        method: 'GET',
    })
}

export const getCloudAgentsProfilesListUrl = (projectId: string, params?: CloudAgentsProfilesListParams) => {
    const normalizedParams = new URLSearchParams()

    Object.entries(params || {}).forEach(([key, value]) => {
        if (value !== undefined) {
            normalizedParams.append(key, value === null ? 'null' : String(value))
        }
    })

    const stringifiedParams = normalizedParams.toString()

    return stringifiedParams.length > 0
        ? `/api/projects/${projectId}/cloud_agents/profiles/?${stringifiedParams}`
        : `/api/projects/${projectId}/cloud_agents/profiles/`
}

/**
 * Base for every cloud_agents viewset: the scope object, the feature flag, and the error mapping.
 * @summary List profiles
 */
export const cloudAgentsProfilesList = async (
    projectId: string,
    params?: CloudAgentsProfilesListParams,
    options?: RequestInit
): Promise<PaginatedProfileListApi> => {
    return apiMutator<PaginatedProfileListApi>(getCloudAgentsProfilesListUrl(projectId, params), {
        ...options,
        method: 'GET',
    })
}

export const getCloudAgentsProfilesCreateUrl = (projectId: string) => {
    return `/api/projects/${projectId}/cloud_agents/profiles/`
}

/**
 * A profile is a named set of run defaults. A run names a profile to use its defaults.
 * @summary Create a profile
 */
export const cloudAgentsProfilesCreate = async (
    projectId: string,
    profileCreateApi: ProfileCreateApi,
    options?: RequestInit
): Promise<ProfileApi> => {
    return apiMutator<ProfileApi>(getCloudAgentsProfilesCreateUrl(projectId), {
        ...options,
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...options?.headers },
        body: JSON.stringify(profileCreateApi),
    })
}

export const getCloudAgentsProfilesRetrieveUrl = (projectId: string, id: string) => {
    return `/api/projects/${projectId}/cloud_agents/profiles/${id}/`
}

/**
 * Base for every cloud_agents viewset: the scope object, the feature flag, and the error mapping.
 * @summary Retrieve a profile
 */
export const cloudAgentsProfilesRetrieve = async (
    projectId: string,
    id: string,
    options?: RequestInit
): Promise<ProfileApi> => {
    return apiMutator<ProfileApi>(getCloudAgentsProfilesRetrieveUrl(projectId, id), {
        ...options,
        method: 'GET',
    })
}

export const getCloudAgentsProfilesPartialUpdateUrl = (projectId: string, id: string) => {
    return `/api/projects/${projectId}/cloud_agents/profiles/${id}/`
}

/**
 * Only the fields in the request change. A null value clears a default.
 * @summary Update a profile
 */
export const cloudAgentsProfilesPartialUpdate = async (
    projectId: string,
    id: string,
    patchedProfileUpdateApi?: PatchedProfileUpdateApi,
    options?: RequestInit
): Promise<ProfileApi> => {
    return apiMutator<ProfileApi>(getCloudAgentsProfilesPartialUpdateUrl(projectId, id), {
        ...options,
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...options?.headers },
        body: JSON.stringify(patchedProfileUpdateApi),
    })
}

export const getCloudAgentsProfilesDestroyUrl = (projectId: string, id: string) => {
    return `/api/projects/${projectId}/cloud_agents/profiles/${id}/`
}

/**
 * Runs that used the profile keep their configuration. The name becomes free.
 * @summary Delete a profile
 */
export const cloudAgentsProfilesDestroy = async (
    projectId: string,
    id: string,
    options?: RequestInit
): Promise<void> => {
    return apiMutator<void>(getCloudAgentsProfilesDestroyUrl(projectId, id), {
        ...options,
        method: 'DELETE',
    })
}

export const getCloudAgentsRunsListUrl = (projectId: string, params?: CloudAgentsRunsListParams) => {
    const normalizedParams = new URLSearchParams()

    Object.entries(params || {}).forEach(([key, value]) => {
        if (value !== undefined) {
            normalizedParams.append(key, value === null ? 'null' : String(value))
        }
    })

    const stringifiedParams = normalizedParams.toString()

    return stringifiedParams.length > 0
        ? `/api/projects/${projectId}/cloud_agents/runs/?${stringifiedParams}`
        : `/api/projects/${projectId}/cloud_agents/runs/`
}

/**
 * The runs of the project, newest first.
 * @summary List runs
 */
export const cloudAgentsRunsList = async (
    projectId: string,
    params?: CloudAgentsRunsListParams,
    options?: RequestInit
): Promise<PaginatedCloudAgentRunListApi> => {
    return apiMutator<PaginatedCloudAgentRunListApi>(getCloudAgentsRunsListUrl(projectId, params), {
        ...options,
        method: 'GET',
    })
}

export const getCloudAgentsRunsCreateUrl = (projectId: string) => {
    return `/api/projects/${projectId}/cloud_agents/runs/`
}

/**
 * Starts a sandbox with a coding agent that works on the prompt in the repository. The response returns at once with a `queued` run. Read the run, stream its events or register a webhook to follow it. Send the same `Idempotency-Key` header again to get the same run and not a second one.
 * @summary Start a run
 */
export const cloudAgentsRunsCreate = async (
    projectId: string,
    cloudAgentRunCreateApi: CloudAgentRunCreateApi,
    options?: RequestInit
): Promise<CloudAgentRunApi> => {
    return apiMutator<CloudAgentRunApi>(getCloudAgentsRunsCreateUrl(projectId), {
        ...options,
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...options?.headers },
        body: JSON.stringify(cloudAgentRunCreateApi),
    })
}

export const getCloudAgentsRunsRetrieveUrl = (projectId: string, id: string) => {
    return `/api/projects/${projectId}/cloud_agents/runs/${id}/`
}

/**
 * Base for every cloud_agents viewset: the scope object, the feature flag, and the error mapping.
 * @summary Retrieve a run
 */
export const cloudAgentsRunsRetrieve = async (
    projectId: string,
    id: string,
    options?: RequestInit
): Promise<CloudAgentRunApi> => {
    return apiMutator<CloudAgentRunApi>(getCloudAgentsRunsRetrieveUrl(projectId, id), {
        ...options,
        method: 'GET',
    })
}

export const getCloudAgentsRunsCancelCreateUrl = (projectId: string, id: string) => {
    return `/api/projects/${projectId}/cloud_agents/runs/${id}/cancel/`
}

/**
 * Asks the run to stop. The response has status 202 and the run can still be `running` for a short time. A run that already stopped is returned with status 200.
 * @summary Cancel a run
 */
export const cloudAgentsRunsCancelCreate = async (
    projectId: string,
    id: string,
    options?: RequestInit
): Promise<CloudAgentRunApi> => {
    return apiMutator<CloudAgentRunApi>(getCloudAgentsRunsCancelCreateUrl(projectId, id), {
        ...options,
        method: 'POST',
    })
}

export const getCloudAgentsRunsEventsRetrieveUrl = (
    projectId: string,
    id: string,
    params?: CloudAgentsRunsEventsRetrieveParams
) => {
    const normalizedParams = new URLSearchParams()

    Object.entries(params || {}).forEach(([key, value]) => {
        if (value !== undefined) {
            normalizedParams.append(key, value === null ? 'null' : String(value))
        }
    })

    const stringifiedParams = normalizedParams.toString()

    return stringifiedParams.length > 0
        ? `/api/projects/${projectId}/cloud_agents/runs/${id}/events/?${stringifiedParams}`
        : `/api/projects/${projectId}/cloud_agents/runs/${id}/events/`
}

/**
 * By default, the response is one JSON object with the stored events of all agent sessions. To follow a live run, send `Accept: text/event-stream`. The response is then a Server-Sent Events stream of the current agent session. Its first frame is `event: run` with the ID, the status and the stop reason of the run. `Last-Event-ID` and `start=latest` apply to the stream only. To resume after a disconnect, send the `id` of the last event in the `Last-Event-ID` header.
 *
 * **SDK consumers**: a generated fetch wrapper buffers the stream. Use the JSON default through it, and read the stream with a streaming `fetch` or an `EventSource` client.
 * @summary Read the events of a run
 */
export const cloudAgentsRunsEventsRetrieve = async (
    projectId: string,
    id: string,
    params?: CloudAgentsRunsEventsRetrieveParams,
    options?: RequestInit
): Promise<CloudAgentRunEventsApi | string> => {
    return apiMutator<CloudAgentRunEventsApi | string>(getCloudAgentsRunsEventsRetrieveUrl(projectId, id, params), {
        ...options,
        method: 'GET',
    })
}

export const getCloudAgentsRunsMessagesCreateUrl = (projectId: string, id: string) => {
    return `/api/projects/${projectId}/cloud_agents/runs/${id}/messages/`
}

/**
 * Sends a follow-up message. An agent that is at work gets the message in its current session. A run that stopped starts a new agent session with the message and goes back to `queued`.
 * @summary Send a message to a run
 */
export const cloudAgentsRunsMessagesCreate = async (
    projectId: string,
    id: string,
    cloudAgentRunMessageApi: CloudAgentRunMessageApi,
    options?: RequestInit
): Promise<CloudAgentRunMessageResponseApi> => {
    return apiMutator<CloudAgentRunMessageResponseApi>(getCloudAgentsRunsMessagesCreateUrl(projectId, id), {
        ...options,
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...options?.headers },
        body: JSON.stringify(cloudAgentRunMessageApi),
    })
}

export const getCloudAgentsRunsUsageRetrieveUrl = (projectId: string, id: string) => {
    return `/api/projects/${projectId}/cloud_agents/runs/${id}/usage/`
}

/**
 * The cost of the run up to now, and each sandbox that it used.
 * @summary Retrieve the usage of a run
 */
export const cloudAgentsRunsUsageRetrieve = async (
    projectId: string,
    id: string,
    options?: RequestInit
): Promise<CloudAgentRunUsageApi> => {
    return apiMutator<CloudAgentRunUsageApi>(getCloudAgentsRunsUsageRetrieveUrl(projectId, id), {
        ...options,
        method: 'GET',
    })
}

export const getCloudAgentsSettingsRetrieveUrl = (projectId: string) => {
    return `/api/projects/${projectId}/cloud_agents/settings/`
}

/**
 * The run defaults and the limits of the project.
 * @summary Retrieve cloud agent settings
 */
export const cloudAgentsSettingsRetrieve = async (
    projectId: string,
    options?: RequestInit
): Promise<CloudAgentSettingsApi> => {
    return apiMutator<CloudAgentSettingsApi>(getCloudAgentsSettingsRetrieveUrl(projectId), {
        ...options,
        method: 'GET',
    })
}

export const getCloudAgentsSettingsPartialUpdateUrl = (projectId: string) => {
    return `/api/projects/${projectId}/cloud_agents/settings/`
}

/**
 * Only the fields in the request change. A null value clears a default.
 * @summary Update cloud agent settings
 */
export const cloudAgentsSettingsPartialUpdate = async (
    projectId: string,
    patchedCloudAgentSettingsUpdateApi?: PatchedCloudAgentSettingsUpdateApi,
    options?: RequestInit
): Promise<CloudAgentSettingsApi> => {
    return apiMutator<CloudAgentSettingsApi>(getCloudAgentsSettingsPartialUpdateUrl(projectId), {
        ...options,
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...options?.headers },
        body: JSON.stringify(patchedCloudAgentSettingsUpdateApi),
    })
}

export const getCloudAgentsUsageRetrieveUrl = (projectId: string, params?: CloudAgentsUsageRetrieveParams) => {
    const normalizedParams = new URLSearchParams()

    Object.entries(params || {}).forEach(([key, value]) => {
        if (value !== undefined) {
            normalizedParams.append(key, value === null ? 'null' : String(value))
        }
    })

    const stringifiedParams = normalizedParams.toString()

    return stringifiedParams.length > 0
        ? `/api/projects/${projectId}/cloud_agents/usage/?${stringifiedParams}`
        : `/api/projects/${projectId}/cloud_agents/usage/`
}

/**
 * Cost and usage totals of the runs created in a date range, for each day or for each profile.
 * @summary Retrieve cloud agents usage
 */
export const cloudAgentsUsageRetrieve = async (
    projectId: string,
    params?: CloudAgentsUsageRetrieveParams,
    options?: RequestInit
): Promise<CloudAgentUsageSummaryApi> => {
    return apiMutator<CloudAgentUsageSummaryApi>(getCloudAgentsUsageRetrieveUrl(projectId, params), {
        ...options,
        method: 'GET',
    })
}

export const getCloudAgentsWebhookEndpointsListUrl = (
    projectId: string,
    params?: CloudAgentsWebhookEndpointsListParams
) => {
    const normalizedParams = new URLSearchParams()

    Object.entries(params || {}).forEach(([key, value]) => {
        if (value !== undefined) {
            normalizedParams.append(key, value === null ? 'null' : String(value))
        }
    })

    const stringifiedParams = normalizedParams.toString()

    return stringifiedParams.length > 0
        ? `/api/projects/${projectId}/cloud_agents/webhook_endpoints/?${stringifiedParams}`
        : `/api/projects/${projectId}/cloud_agents/webhook_endpoints/`
}

/**
 * Base for every cloud_agents viewset: the scope object, the feature flag, and the error mapping.
 * @summary List webhook endpoints
 */
export const cloudAgentsWebhookEndpointsList = async (
    projectId: string,
    params?: CloudAgentsWebhookEndpointsListParams,
    options?: RequestInit
): Promise<PaginatedWebhookEndpointListApi> => {
    return apiMutator<PaginatedWebhookEndpointListApi>(getCloudAgentsWebhookEndpointsListUrl(projectId, params), {
        ...options,
        method: 'GET',
    })
}

export const getCloudAgentsWebhookEndpointsCreateUrl = (projectId: string) => {
    return `/api/projects/${projectId}/cloud_agents/webhook_endpoints/`
}

/**
 * PostHog sends run events to the URL as signed POST requests. A project can have 5 endpoints.
 * @summary Create a webhook endpoint
 */
export const cloudAgentsWebhookEndpointsCreate = async (
    projectId: string,
    webhookEndpointCreateApi: WebhookEndpointCreateApi,
    options?: RequestInit
): Promise<WebhookEndpointApi> => {
    return apiMutator<WebhookEndpointApi>(getCloudAgentsWebhookEndpointsCreateUrl(projectId), {
        ...options,
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...options?.headers },
        body: JSON.stringify(webhookEndpointCreateApi),
    })
}

export const getCloudAgentsWebhookEndpointsRetrieveUrl = (projectId: string, id: string) => {
    return `/api/projects/${projectId}/cloud_agents/webhook_endpoints/${id}/`
}

/**
 * Base for every cloud_agents viewset: the scope object, the feature flag, and the error mapping.
 * @summary Retrieve a webhook endpoint
 */
export const cloudAgentsWebhookEndpointsRetrieve = async (
    projectId: string,
    id: string,
    options?: RequestInit
): Promise<WebhookEndpointApi> => {
    return apiMutator<WebhookEndpointApi>(getCloudAgentsWebhookEndpointsRetrieveUrl(projectId, id), {
        ...options,
        method: 'GET',
    })
}

export const getCloudAgentsWebhookEndpointsPartialUpdateUrl = (projectId: string, id: string) => {
    return `/api/projects/${projectId}/cloud_agents/webhook_endpoints/${id}/`
}

/**
 * Base for every cloud_agents viewset: the scope object, the feature flag, and the error mapping.
 * @summary Update a webhook endpoint
 */
export const cloudAgentsWebhookEndpointsPartialUpdate = async (
    projectId: string,
    id: string,
    patchedWebhookEndpointUpdateApi?: PatchedWebhookEndpointUpdateApi,
    options?: RequestInit
): Promise<WebhookEndpointApi> => {
    return apiMutator<WebhookEndpointApi>(getCloudAgentsWebhookEndpointsPartialUpdateUrl(projectId, id), {
        ...options,
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json', ...options?.headers },
        body: JSON.stringify(patchedWebhookEndpointUpdateApi),
    })
}

export const getCloudAgentsWebhookEndpointsDestroyUrl = (projectId: string, id: string) => {
    return `/api/projects/${projectId}/cloud_agents/webhook_endpoints/${id}/`
}

/**
 * Base for every cloud_agents viewset: the scope object, the feature flag, and the error mapping.
 * @summary Delete a webhook endpoint
 */
export const cloudAgentsWebhookEndpointsDestroy = async (
    projectId: string,
    id: string,
    options?: RequestInit
): Promise<void> => {
    return apiMutator<void>(getCloudAgentsWebhookEndpointsDestroyUrl(projectId, id), {
        ...options,
        method: 'DELETE',
    })
}

export const getCloudAgentsWebhookEndpointsTestCreateUrl = (projectId: string, id: string) => {
    return `/api/projects/${projectId}/cloud_agents/webhook_endpoints/${id}/test/`
}

/**
 * Sends a `run.test` event to the endpoint, also when the endpoint is disabled.
 * @summary Send a test event
 */
export const cloudAgentsWebhookEndpointsTestCreate = async (
    projectId: string,
    id: string,
    options?: RequestInit
): Promise<WebhookTestApi> => {
    return apiMutator<WebhookTestApi>(getCloudAgentsWebhookEndpointsTestCreateUrl(projectId, id), {
        ...options,
        method: 'POST',
    })
}

export const getCloudAgentsWebhookEndpointsDeliveriesListUrl = (projectId: string) => {
    return `/api/projects/${projectId}/cloud_agents/webhook_endpoints/deliveries/`
}

/**
 * The last 50 deliveries of the project, newest first.
 * @summary List recent webhook deliveries
 */
export const cloudAgentsWebhookEndpointsDeliveriesList = async (
    projectId: string,
    options?: RequestInit
): Promise<WebhookDeliveryApi[]> => {
    return apiMutator<WebhookDeliveryApi[]>(getCloudAgentsWebhookEndpointsDeliveriesListUrl(projectId), {
        ...options,
        method: 'GET',
    })
}

export const getCloudAgentsWebhookEndpointsRotateSecretCreateUrl = (projectId: string) => {
    return `/api/projects/${projectId}/cloud_agents/webhook_endpoints/rotate_secret/`
}

/**
 * Replaces the signing secret and returns the new one. The old secret stops working immediately.
 * @summary Rotate the webhook signing secret
 */
export const cloudAgentsWebhookEndpointsRotateSecretCreate = async (
    projectId: string,
    options?: RequestInit
): Promise<WebhookSecretApi> => {
    return apiMutator<WebhookSecretApi>(getCloudAgentsWebhookEndpointsRotateSecretCreateUrl(projectId), {
        ...options,
        method: 'POST',
    })
}

export const getCloudAgentsWebhookEndpointsSecretCreateUrl = (projectId: string) => {
    return `/api/projects/${projectId}/cloud_agents/webhook_endpoints/secret/`
}

/**
 * Creates the signing secret of the project and returns it one time. When the project already has a secret, the response has no secret: rotate the secret to get a new one.
 * @summary Create the webhook signing secret
 */
export const cloudAgentsWebhookEndpointsSecretCreate = async (
    projectId: string,
    options?: RequestInit
): Promise<WebhookSecretApi> => {
    return apiMutator<WebhookSecretApi>(getCloudAgentsWebhookEndpointsSecretCreateUrl(projectId), {
        ...options,
        method: 'POST',
    })
}
