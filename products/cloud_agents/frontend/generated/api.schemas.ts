/**
 * Auto-generated from the Django backend OpenAPI schema.
 * To modify these types, update the Django serializers or views, then run:
 *   hogli build:openapi
 * Questions or issues? #team-devex on Slack
 *
 * PostHog API - generated
 * OpenAPI spec version: 1.0.0
 */
/**
 * * `1x2` - 1 vCPU, 2 GiB
 * * `2x4` - 2 vCPU, 4 GiB
 * * `2x8` - 2 vCPU, 8 GiB
 * * `4x8` - 4 vCPU, 8 GiB
 * * `4x16` - 4 vCPU, 16 GiB
 * * `8x16` - 8 vCPU, 16 GiB
 * * `8x32` - 8 vCPU, 32 GiB
 * * `16x64` - 16 vCPU, 64 GiB
 */
export type SizeNameEnumApi = (typeof SizeNameEnumApi)[keyof typeof SizeNameEnumApi]

export const SizeNameEnumApi = {
    '1x2': '1x2',
    '2x4': '2x4',
    '2x8': '2x8',
    '4x8': '4x8',
    '4x16': '4x16',
    '8x16': '8x16',
    '8x32': '8x32',
    '16x64': '16x64',
} as const

export interface CloudAgentSizeApi {
    /** Name of the size, as `<vCPU>x<memory in GiB>`.
     *
     * * `1x2` - 1 vCPU, 2 GiB
     * * `2x4` - 2 vCPU, 4 GiB
     * * `2x8` - 2 vCPU, 8 GiB
     * * `4x8` - 4 vCPU, 8 GiB
     * * `4x16` - 4 vCPU, 16 GiB
     * * `8x16` - 8 vCPU, 16 GiB
     * * `8x32` - 8 vCPU, 32 GiB
     * * `16x64` - 16 vCPU, 64 GiB */
    name: SizeNameEnumApi
    /** Number of vCPUs of the sandbox. */
    vcpu: number
    /** Memory of the sandbox in GiB. */
    memory_gib: number
    /**
     * Compute price of one hour of this size in US dollars, as a decimal string.
     * @pattern ^-?\d{0,6}(?:\.\d{0,6})?$
     */
    price_per_hour_usd: string
}

export interface CloudAgentModelApi {
    /** ID of the model. Use it as `model` when you start a run. */
    id: string
    /** Display name of the model. */
    name: string
    /** The agent runtime that drives the model. */
    runtime_adapter: string
    /** Whether a run with no model uses this model. */
    is_default: boolean
}

/**
 * * `auto` - Auto
 * * `own_key` - Own Key
 * * `own_subscription` - Own Subscription
 * * `posthog` - PostHog
 */
export type InferenceModeEnumApi = (typeof InferenceModeEnumApi)[keyof typeof InferenceModeEnumApi]

export const InferenceModeEnumApi = {
    Auto: 'auto',
    OwnKey: 'own_key',
    OwnSubscription: 'own_subscription',
    Posthog: 'posthog',
} as const

export interface CloudAgentRateCardApi {
    /**
     * Price of one vCPU for one hour in US dollars, as a decimal string.
     * @pattern ^-?\d{0,6}(?:\.\d{0,6})?$
     */
    vcpu_hour_usd: string
    /**
     * Price of one GiB of memory for one hour in US dollars, as a decimal string.
     * @pattern ^-?\d{0,6}(?:\.\d{0,6})?$
     */
    memory_gib_hour_usd: string
    /** Version of the price list. */
    version: string
}

export interface CloudAgentLimitsApi {
    /** How many runs the project can have active at the same time. */
    max_concurrent_runs: number
    /** How many runs the project can start in one hour. */
    create_rate_per_hour: number
}

export interface CloudAgentCatalogApi {
    /** The sandbox sizes that a run can use. */
    sizes: CloudAgentSizeApi[]
    /** The models that a run can use. */
    models: CloudAgentModelApi[]
    /** The values that `inference` accepts. */
    inference_modes: InferenceModeEnumApi[]
    /** The compute prices that the size prices come from. */
    rates: CloudAgentRateCardApi
    /** The limits of this project. */
    limits: CloudAgentLimitsApi
}

export interface CloudAgentEstimateApi {
    /** The sandbox size that was priced.
     *
     * * `1x2` - 1 vCPU, 2 GiB
     * * `2x4` - 2 vCPU, 4 GiB
     * * `2x8` - 2 vCPU, 8 GiB
     * * `4x8` - 4 vCPU, 8 GiB
     * * `4x16` - 4 vCPU, 16 GiB
     * * `8x16` - 8 vCPU, 16 GiB
     * * `8x32` - 8 vCPU, 32 GiB
     * * `16x64` - 16 vCPU, 64 GiB */
    size: SizeNameEnumApi
    /** How many minutes the sandbox is up. */
    minutes: number
    /**
     * Compute price of one hour of this size in US dollars, as a decimal string.
     * @pattern ^-?\d{0,6}(?:\.\d{0,6})?$
     */
    price_per_hour_usd: string
    /**
     * Compute cost for the given minutes in US dollars, as a decimal string. Model usage is not included.
     * @pattern ^-?\d{0,10}(?:\.\d{0,4})?$
     */
    estimate_usd: string
}

/**
 * * `draft` - Draft
 * * `ready` - Ready
 */
export type PrModeEnumApi = (typeof PrModeEnumApi)[keyof typeof PrModeEnumApi]

export const PrModeEnumApi = {
    Draft: 'draft',
    Ready: 'ready',
} as const

/**
 * The run defaults that a profile and the project settings share. A null value sets no default.
 */
export interface ProfileApi {
    /**
     * Default GitHub repository, in the format `owner/name`. Null sets no default.
     * @maxLength 255
     * @nullable
     * @pattern ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$
     */
    repository?: string | null
    /**
     * Default base branch. Null uses the default branch of the repository.
     * @maxLength 255
     * @nullable
     */
    branch?: string | null
    /**
     * Default model for the agent. Null lets PostHog select the model.
     * @maxLength 100
     * @nullable
     */
    model?: string | null
    /** Default sandbox size, as `<vCPU>x<memory in GiB>`. Null uses the product default.
     *
     * * `1x2` - 1 vCPU, 2 GiB
     * * `2x4` - 2 vCPU, 4 GiB
     * * `2x8` - 2 vCPU, 8 GiB
     * * `4x8` - 4 vCPU, 8 GiB
     * * `4x16` - 4 vCPU, 16 GiB
     * * `8x16` - 8 vCPU, 16 GiB
     * * `8x32` - 8 vCPU, 32 GiB
     * * `16x64` - 16 vCPU, 64 GiB */
    size?: SizeNameEnumApi | null
    /** How the agent pays for model usage. `auto` uses your own key or subscription when one is connected, and PostHog inference otherwise. Null uses the product default.
     *
     * * `auto` - Auto
     * * `own_key` - Own Key
     * * `own_subscription` - Own Subscription
     * * `posthog` - PostHog */
    inference?: InferenceModeEnumApi | null
    /**
     * Instructions that the agent gets before the prompt. Project instructions come first, then profile instructions, then the instructions of the run.
     * @maxLength 20000
     * @nullable
     */
    instructions?: string | null
    /**
     * Whether the agent opens a pull request when it finishes. Null uses the product default.
     * @nullable
     */
    create_pr?: boolean | null
    /** Whether the pull request opens as a draft or ready for review. Null uses the product default.
     *
     * * `draft` - Draft
     * * `ready` - Ready */
    pr_mode?: PrModeEnumApi | null
    /**
     * The run stops after this many minutes, from 5 to 240. Null uses the product default.
     * @minimum 5
     * @maximum 240
     * @nullable
     */
    max_duration_minutes?: number | null
    /**
     * Cost limit of a run in US dollars. Reserved. Not enforced yet. Null sets no cost limit.
     * @nullable
     * @pattern ^-?\d{0,8}(?:\.\d{0,2})?$
     */
    max_cost_usd?: string | null
    /** ID of the profile. */
    id: string
    /** Name of the profile. */
    name: string
    /** What this profile is for. */
    description: string
    /**
     * Tags added to every run that uses this profile.
     * @maxItems 20
     * @items.maxLength 50
     */
    tags: string[]
    /**
     * HTTPS URL that gets the events of every run that uses this profile.
     * @nullable
     */
    webhook_url: string | null
    /**
     * ID of the user who created the profile.
     * @nullable
     */
    created_by: number | null
    /** When the profile was created. */
    created_at: string
    /** When the profile was last changed. */
    updated_at: string
}

export interface PaginatedProfileListApi {
    count: number
    /** @nullable */
    next?: string | null
    /** @nullable */
    previous?: string | null
    results: ProfileApi[]
}

/**
 * The run defaults that a profile and the project settings share. A null value sets no default.
 */
export interface ProfileCreateApi {
    /**
     * Default GitHub repository, in the format `owner/name`. Null sets no default.
     * @maxLength 255
     * @nullable
     * @pattern ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$
     */
    repository?: string | null
    /**
     * Default base branch. Null uses the default branch of the repository.
     * @maxLength 255
     * @nullable
     */
    branch?: string | null
    /**
     * Default model for the agent. Null lets PostHog select the model.
     * @maxLength 100
     * @nullable
     */
    model?: string | null
    /** Default sandbox size, as `<vCPU>x<memory in GiB>`. Null uses the product default.
     *
     * * `1x2` - 1 vCPU, 2 GiB
     * * `2x4` - 2 vCPU, 4 GiB
     * * `2x8` - 2 vCPU, 8 GiB
     * * `4x8` - 4 vCPU, 8 GiB
     * * `4x16` - 4 vCPU, 16 GiB
     * * `8x16` - 8 vCPU, 16 GiB
     * * `8x32` - 8 vCPU, 32 GiB
     * * `16x64` - 16 vCPU, 64 GiB */
    size?: SizeNameEnumApi | null
    /** How the agent pays for model usage. `auto` uses your own key or subscription when one is connected, and PostHog inference otherwise. Null uses the product default.
     *
     * * `auto` - Auto
     * * `own_key` - Own Key
     * * `own_subscription` - Own Subscription
     * * `posthog` - PostHog */
    inference?: InferenceModeEnumApi | null
    /**
     * Instructions that the agent gets before the prompt. Project instructions come first, then profile instructions, then the instructions of the run.
     * @maxLength 20000
     * @nullable
     */
    instructions?: string | null
    /**
     * Whether the agent opens a pull request when it finishes. Null uses the product default.
     * @nullable
     */
    create_pr?: boolean | null
    /** Whether the pull request opens as a draft or ready for review. Null uses the product default.
     *
     * * `draft` - Draft
     * * `ready` - Ready */
    pr_mode?: PrModeEnumApi | null
    /**
     * The run stops after this many minutes, from 5 to 240. Null uses the product default.
     * @minimum 5
     * @maximum 240
     * @nullable
     */
    max_duration_minutes?: number | null
    /**
     * Cost limit of a run in US dollars. Reserved. Not enforced yet. Null sets no cost limit.
     * @nullable
     * @pattern ^-?\d{0,8}(?:\.\d{0,2})?$
     */
    max_cost_usd?: string | null
    /**
     * What this profile is for.
     * @maxLength 2000
     */
    description?: string
    /**
     * Tags added to every run that uses this profile.
     * @maxItems 20
     * @items.maxLength 50
     */
    tags?: string[]
    /**
     * HTTPS URL that gets the events of every run that uses this profile. Null sends none.
     * @maxLength 2000
     * @nullable
     */
    webhook_url?: string | null
    /**
     * Name of the profile. It is unique in the project, without regard to case.
     * @maxLength 100
     */
    name: string
}

/**
 * The run defaults that a profile and the project settings share. A null value sets no default.
 */
export interface PatchedProfileUpdateApi {
    /**
     * Default GitHub repository, in the format `owner/name`. Null sets no default.
     * @maxLength 255
     * @nullable
     * @pattern ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$
     */
    repository?: string | null
    /**
     * Default base branch. Null uses the default branch of the repository.
     * @maxLength 255
     * @nullable
     */
    branch?: string | null
    /**
     * Default model for the agent. Null lets PostHog select the model.
     * @maxLength 100
     * @nullable
     */
    model?: string | null
    /** Default sandbox size, as `<vCPU>x<memory in GiB>`. Null uses the product default.
     *
     * * `1x2` - 1 vCPU, 2 GiB
     * * `2x4` - 2 vCPU, 4 GiB
     * * `2x8` - 2 vCPU, 8 GiB
     * * `4x8` - 4 vCPU, 8 GiB
     * * `4x16` - 4 vCPU, 16 GiB
     * * `8x16` - 8 vCPU, 16 GiB
     * * `8x32` - 8 vCPU, 32 GiB
     * * `16x64` - 16 vCPU, 64 GiB */
    size?: SizeNameEnumApi | null
    /** How the agent pays for model usage. `auto` uses your own key or subscription when one is connected, and PostHog inference otherwise. Null uses the product default.
     *
     * * `auto` - Auto
     * * `own_key` - Own Key
     * * `own_subscription` - Own Subscription
     * * `posthog` - PostHog */
    inference?: InferenceModeEnumApi | null
    /**
     * Instructions that the agent gets before the prompt. Project instructions come first, then profile instructions, then the instructions of the run.
     * @maxLength 20000
     * @nullable
     */
    instructions?: string | null
    /**
     * Whether the agent opens a pull request when it finishes. Null uses the product default.
     * @nullable
     */
    create_pr?: boolean | null
    /** Whether the pull request opens as a draft or ready for review. Null uses the product default.
     *
     * * `draft` - Draft
     * * `ready` - Ready */
    pr_mode?: PrModeEnumApi | null
    /**
     * The run stops after this many minutes, from 5 to 240. Null uses the product default.
     * @minimum 5
     * @maximum 240
     * @nullable
     */
    max_duration_minutes?: number | null
    /**
     * Cost limit of a run in US dollars. Reserved. Not enforced yet. Null sets no cost limit.
     * @nullable
     * @pattern ^-?\d{0,8}(?:\.\d{0,2})?$
     */
    max_cost_usd?: string | null
    /**
     * What this profile is for.
     * @maxLength 2000
     */
    description?: string
    /**
     * Tags added to every run that uses this profile.
     * @maxItems 20
     * @items.maxLength 50
     */
    tags?: string[]
    /**
     * HTTPS URL that gets the events of every run that uses this profile. Null sends none.
     * @maxLength 2000
     * @nullable
     */
    webhook_url?: string | null
    /**
     * Name of the profile. It is unique in the project, without regard to case.
     * @maxLength 100
     */
    name?: string
}

/**
 * * `queued` - Queued
 * * `running` - Running
 * * `completed` - Completed
 * * `failed` - Failed
 * * `cancelled` - Cancelled
 */
export type CloudAgentRunStatusEnumApi = (typeof CloudAgentRunStatusEnumApi)[keyof typeof CloudAgentRunStatusEnumApi]

export const CloudAgentRunStatusEnumApi = {
    Queued: 'queued',
    Running: 'running',
    Completed: 'completed',
    Failed: 'failed',
    Cancelled: 'cancelled',
} as const

/**
 * * `done` - Done
 * * `cancelled` - Cancelled
 * * `error` - Error
 * * `timeout` - Timeout
 * * `budget_exceeded` - Budget Exceeded
 * * `usage_limit` - Usage Limit
 */
export type StopReasonEnumApi = (typeof StopReasonEnumApi)[keyof typeof StopReasonEnumApi]

export const StopReasonEnumApi = {
    Done: 'done',
    Cancelled: 'cancelled',
    Error: 'error',
    Timeout: 'timeout',
    BudgetExceeded: 'budget_exceeded',
    UsageLimit: 'usage_limit',
} as const

export interface CloudAgentRunProfileRefApi {
    /** ID of the profile. */
    id: string
    /** Name of the profile. */
    name: string
}

/**
 * Reads a run: the stored configuration is in `config`, and the priced size is on the run.
 */
export interface CloudAgentRunConfigApi {
    /**
     * Model that the agent uses.
     * @nullable
     */
    model: string | null
    /** Sandbox size of the run. It is fixed for the life of the run. */
    size: CloudAgentSizeApi
    /** How the run pays for model usage: `posthog` for PostHog inference, `own_key` for the API key of the user, `own_subscription` for the subscription of the user.
     *
     * * `auto` - Auto
     * * `own_key` - Own Key
     * * `own_subscription` - Own Subscription
     * * `posthog` - PostHog */
    inference: InferenceModeEnumApi
    /** Whether the agent opens a pull request when it finishes. */
    create_pr: boolean
    /** Whether the pull request opens as a draft or ready for review.
     *
     * * `draft` - Draft
     * * `ready` - Ready */
    pr_mode: PrModeEnumApi
    /** Time limit of the run in minutes. */
    max_duration_minutes: number
    /**
     * Cost limit of the run in US dollars. Reserved. Not enforced yet.
     * @nullable
     * @pattern ^-?\d{0,8}(?:\.\d{0,2})?$
     */
    max_cost_usd: string | null
    /** Whether the agent got instructions from the run, its profile or the project settings. */
    readonly instructions_applied: boolean
}

export interface CloudAgentRunResultApi {
    /**
     * URL of the pull request that the agent opened last.
     * @nullable
     */
    pr_url: string | null
    /** URLs of all pull requests that the agent opened. */
    pr_urls: string[]
    /**
     * Summary of the work, written by the agent.
     * @nullable
     */
    summary: string | null
}

/**
 * * `billed` - Billed
 * * `unbilled` - Unbilled
 */
export type BillingModeEnumApi = (typeof BillingModeEnumApi)[keyof typeof BillingModeEnumApi]

export const BillingModeEnumApi = {
    Billed: 'billed',
    Unbilled: 'unbilled',
} as const

/**
 * * `posthog` - PostHog
 * * `own_key` - Own Key
 * * `own_subscription` - Own Subscription
 */
export type InferenceBillingEnumApi = (typeof InferenceBillingEnumApi)[keyof typeof InferenceBillingEnumApi]

export const InferenceBillingEnumApi = {
    Posthog: 'posthog',
    OwnKey: 'own_key',
    OwnSubscription: 'own_subscription',
} as const

export interface CloudAgentRunCostApi {
    /**
     * Compute cost in US dollars, as a decimal string. Null until the first sandbox reports usage.
     * @nullable
     * @pattern ^-?\d{0,10}(?:\.\d{0,4})?$
     */
    compute_usd: string | null
    /**
     * Model usage cost in US dollars, as a decimal string. Null when the run uses your own key or subscription, because you pay the model provider directly.
     * @nullable
     * @pattern ^-?\d{0,10}(?:\.\d{0,4})?$
     */
    inference_usd: string | null
    /**
     * Sum of the compute cost and the model usage cost, as a decimal string. Null until the compute cost is known.
     * @nullable
     * @pattern ^-?\d{0,10}(?:\.\d{0,4})?$
     */
    total_usd: string | null
    /**
     * vCPU seconds that the run used.
     * @nullable
     * @pattern ^-?\d{0,13}(?:\.\d{0,3})?$
     */
    vcpu_seconds: string | null
    /**
     * GiB seconds of memory that the run used.
     * @nullable
     * @pattern ^-?\d{0,13}(?:\.\d{0,3})?$
     */
    gib_seconds: string | null
    /** `billed` when the project pays for the run, `unbilled` when it does not.
     *
     * * `billed` - Billed
     * * `unbilled` - Unbilled */
    billing_mode: BillingModeEnumApi
    /** Who pays for the model usage of the run.
     *
     * * `posthog` - PostHog
     * * `own_key` - Own Key
     * * `own_subscription` - Own Subscription */
    inference_billing: InferenceBillingEnumApi | null
    /** Whether the cost is final. The cost can still change for a short time after the run stops. */
    final: boolean
}

export interface CloudAgentAgentSessionApi {
    /** Position of the session in the run, from 1. */
    index: number
    /** Status of the session.
     *
     * * `queued` - Queued
     * * `running` - Running
     * * `completed` - Completed
     * * `failed` - Failed
     * * `cancelled` - Cancelled */
    status: CloudAgentRunStatusEnumApi
    /**
     * When the agent started work in this session.
     * @nullable
     */
    started_at: string | null
    /**
     * When the session ended.
     * @nullable
     */
    ended_at: string | null
}

export interface CloudAgentRunCreatedByApi {
    /** ID of the user. */
    id: number
    /**
     * Email address of the user.
     * @nullable
     */
    email: string | null
}

/**
 * * `api` - API
 * * `app` - App
 * * `internal` - Internal
 */
export type CallerKindEnumApi = (typeof CallerKindEnumApi)[keyof typeof CallerKindEnumApi]

export const CallerKindEnumApi = {
    Api: 'api',
    App: 'app',
    Internal: 'internal',
} as const

/**
 * Your own key and value pairs.
 */
export type CloudAgentRunApiMetadata = { [key: string]: string }

export interface CloudAgentRunApi {
    /** ID of the run. */
    id: string
    /** `queued` waits for a sandbox, `running` has an agent at work, and `completed`, `failed` and `cancelled` are final until you send a new message.
     *
     * * `queued` - Queued
     * * `running` - Running
     * * `completed` - Completed
     * * `failed` - Failed
     * * `cancelled` - Cancelled */
    status: CloudAgentRunStatusEnumApi
    /** Why the run stopped. Null while the run is active.
     *
     * * `done` - Done
     * * `cancelled` - Cancelled
     * * `error` - Error
     * * `timeout` - Timeout
     * * `budget_exceeded` - Budget Exceeded
     * * `usage_limit` - Usage Limit */
    stop_reason: StopReasonEnumApi | null
    /**
     * What went wrong and what to do next. Null when the run has no error.
     * @nullable
     */
    error: string | null
    /** When the run was created. */
    created_at: string
    /**
     * When the agent first started work.
     * @nullable
     */
    started_at: string | null
    /**
     * When the run stopped.
     * @nullable
     */
    completed_at: string | null
    /** When the run last changed. */
    updated_at: string
    /** The task that the run started with. */
    prompt: string
    /** GitHub repository of the run, in the format `owner/name`. */
    repository: string
    /**
     * Base branch of the run. Null uses the default branch of the repository.
     * @nullable
     */
    branch: string | null
    /** The profile that the run used. Null when it used none. */
    readonly profile: CloudAgentRunProfileRefApi | null
    /** The configuration that the run uses. */
    config: CloudAgentRunConfigApi
    /** What the agent produced. */
    result: CloudAgentRunResultApi
    /** What the run cost. */
    cost: CloudAgentRunCostApi
    /** The agent sessions of the run, oldest first. A message to a run that stopped starts a new session. */
    agent_sessions: CloudAgentAgentSessionApi[]
    /**
     * Tags of the run, including the tags of its profile.
     * @maxItems 20
     * @items.maxLength 50
     */
    tags: string[]
    /** Your own key and value pairs. */
    metadata: CloudAgentRunApiMetadata
    /** The user who started the run. Null when the user no longer exists. */
    readonly created_by: CloudAgentRunCreatedByApi | null
    /** `api` for an API client, `app` for the PostHog app, `internal` for a PostHog product.
     *
     * * `api` - API
     * * `app` - App
     * * `internal` - Internal */
    caller: CallerKindEnumApi
}

export interface PaginatedCloudAgentRunListApi {
    count: number
    /** @nullable */
    next?: string | null
    /** @nullable */
    previous?: string | null
    results: CloudAgentRunApi[]
}

/**
 * Your own key and value pairs, stored with the run and returned with it. At most 16 pairs. Keys and values are strings.
 */
export type CloudAgentRunCreateApiMetadata = { [key: string]: string }

/**
 * The run defaults that a profile and the project settings share. A null value sets no default.
 */
export interface CloudAgentRunCreateApi {
    /**
     * GitHub repository that the agent works in, in the format `owner/name`. Required unless the profile or the project settings set a default.
     * @maxLength 255
     * @nullable
     * @pattern ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$
     */
    repository?: string | null
    /**
     * Default base branch. Null uses the default branch of the repository.
     * @maxLength 255
     * @nullable
     */
    branch?: string | null
    /**
     * Default model for the agent. Null lets PostHog select the model.
     * @maxLength 100
     * @nullable
     */
    model?: string | null
    /** Default sandbox size, as `<vCPU>x<memory in GiB>`. Null uses the product default.
     *
     * * `1x2` - 1 vCPU, 2 GiB
     * * `2x4` - 2 vCPU, 4 GiB
     * * `2x8` - 2 vCPU, 8 GiB
     * * `4x8` - 4 vCPU, 8 GiB
     * * `4x16` - 4 vCPU, 16 GiB
     * * `8x16` - 8 vCPU, 16 GiB
     * * `8x32` - 8 vCPU, 32 GiB
     * * `16x64` - 16 vCPU, 64 GiB */
    size?: SizeNameEnumApi | null
    /** How the agent pays for model usage. `auto` uses your own key or subscription when one is connected, and PostHog inference otherwise. Null uses the product default.
     *
     * * `auto` - Auto
     * * `own_key` - Own Key
     * * `own_subscription` - Own Subscription
     * * `posthog` - PostHog */
    inference?: InferenceModeEnumApi | null
    /**
     * Instructions that the agent gets before the prompt. Project instructions come first, then profile instructions, then the instructions of the run.
     * @maxLength 20000
     * @nullable
     */
    instructions?: string | null
    /**
     * Whether the agent opens a pull request when it finishes. Null uses the product default.
     * @nullable
     */
    create_pr?: boolean | null
    /** Whether the pull request opens as a draft or ready for review. Null uses the product default.
     *
     * * `draft` - Draft
     * * `ready` - Ready */
    pr_mode?: PrModeEnumApi | null
    /**
     * The run stops after this many minutes, from 5 to 240. Null uses the product default.
     * @minimum 5
     * @maximum 240
     * @nullable
     */
    max_duration_minutes?: number | null
    /**
     * Cost limit of a run in US dollars. Reserved. Not enforced yet. Null sets no cost limit.
     * @nullable
     * @pattern ^-?\d{0,8}(?:\.\d{0,2})?$
     */
    max_cost_usd?: string | null
    /**
     * The task for the agent, in plain language.
     * @maxLength 64000
     */
    prompt: string
    /**
     * ID or name of the profile whose defaults the run uses. Null uses the default profile of the project, when one is set.
     * @maxLength 100
     * @nullable
     */
    profile?: string | null
    /**
     * Tags for the run. The tags of the profile are added to them.
     * @maxItems 20
     * @items.maxLength 50
     */
    tags?: string[]
    /** Your own key and value pairs, stored with the run and returned with it. At most 16 pairs. Keys and values are strings. */
    metadata?: CloudAgentRunCreateApiMetadata
    /**
     * HTTPS URL that gets the events of this run, in addition to the webhook endpoints of the project.
     * @maxLength 2000
     * @nullable
     */
    webhook_url?: string | null
}

export type CloudAgentRunEventsApiEventsItem = { [key: string]: unknown }

export interface CloudAgentRunEventsApi {
    /** The stored events of the run, oldest first, across all agent sessions. Each event is one agent protocol message with the time it was recorded. */
    events: CloudAgentRunEventsApiEventsItem[]
    /** True when the event log is too large to return in full. The response then has the earliest agent sessions that fit. */
    truncated: boolean
}

export interface CloudAgentRunMessageApi {
    /**
     * The follow-up message for the agent, in plain language.
     * @maxLength 64000
     */
    content: string
}

export interface CloudAgentRunMessageResponseApi {
    /** True when the message started a new agent session, because the run had stopped. False when the running agent got the message. */
    resumed: boolean
    /** The run after the message. */
    run: CloudAgentRunApi
}

export interface CloudAgentSandboxSessionUsageApi {
    /**
     * Number of vCPUs of the sandbox.
     * @pattern ^-?\d{0,5}(?:\.\d{0,3})?$
     */
    vcpu: string
    /**
     * Memory of the sandbox in GiB.
     * @pattern ^-?\d{0,5}(?:\.\d{0,3})?$
     */
    memory_gib: string
    /** When the sandbox started. */
    started_at: string
    /**
     * When the sandbox stopped. Null while it is up.
     * @nullable
     */
    ended_at: string | null
    /** How many seconds of the sandbox count for the cost. */
    seconds: number
    /**
     * Compute cost of the sandbox in US dollars, as a decimal string.
     * @pattern ^-?\d{0,10}(?:\.\d{0,4})?$
     */
    cost_usd: string
    /** Whether PostHog waived the cost of this sandbox. */
    waived: boolean
}

export interface CloudAgentRunUsageApi {
    /** ID of the run. */
    run_id: string
    /** What the run cost up to now. */
    cost: CloudAgentRunCostApi
    /** The sandboxes of the run, oldest first. */
    sessions: CloudAgentSandboxSessionUsageApi[]
}

/**
 * The run defaults that a profile and the project settings share. A null value sets no default.
 */
export interface CloudAgentSettingsApi {
    /**
     * Default GitHub repository, in the format `owner/name`. Null sets no default.
     * @maxLength 255
     * @nullable
     * @pattern ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$
     */
    repository?: string | null
    /**
     * Default base branch. Null uses the default branch of the repository.
     * @maxLength 255
     * @nullable
     */
    branch?: string | null
    /**
     * Default model for the agent. Null lets PostHog select the model.
     * @maxLength 100
     * @nullable
     */
    model?: string | null
    /** Default sandbox size, as `<vCPU>x<memory in GiB>`. Null uses the product default.
     *
     * * `1x2` - 1 vCPU, 2 GiB
     * * `2x4` - 2 vCPU, 4 GiB
     * * `2x8` - 2 vCPU, 8 GiB
     * * `4x8` - 4 vCPU, 8 GiB
     * * `4x16` - 4 vCPU, 16 GiB
     * * `8x16` - 8 vCPU, 16 GiB
     * * `8x32` - 8 vCPU, 32 GiB
     * * `16x64` - 16 vCPU, 64 GiB */
    size?: SizeNameEnumApi | null
    /** How the agent pays for model usage. `auto` uses your own key or subscription when one is connected, and PostHog inference otherwise. Null uses the product default.
     *
     * * `auto` - Auto
     * * `own_key` - Own Key
     * * `own_subscription` - Own Subscription
     * * `posthog` - PostHog */
    inference?: InferenceModeEnumApi | null
    /**
     * Instructions that the agent gets before the prompt. Project instructions come first, then profile instructions, then the instructions of the run.
     * @maxLength 20000
     * @nullable
     */
    instructions?: string | null
    /**
     * Whether the agent opens a pull request when it finishes. Null uses the product default.
     * @nullable
     */
    create_pr?: boolean | null
    /** Whether the pull request opens as a draft or ready for review. Null uses the product default.
     *
     * * `draft` - Draft
     * * `ready` - Ready */
    pr_mode?: PrModeEnumApi | null
    /**
     * The run stops after this many minutes, from 5 to 240. Null uses the product default.
     * @minimum 5
     * @maximum 240
     * @nullable
     */
    max_duration_minutes?: number | null
    /**
     * Cost limit of a run in US dollars. Reserved. Not enforced yet. Null sets no cost limit.
     * @nullable
     * @pattern ^-?\d{0,8}(?:\.\d{0,2})?$
     */
    max_cost_usd?: string | null
    /**
     * ID of the profile that a run uses when it names no profile.
     * @nullable
     */
    default_profile: string | null
    /** How many runs the project can have active at the same time. */
    max_concurrent_runs: number
    /** How many runs the project can start in one hour. */
    create_rate_per_hour: number
    /** Whether the project has a webhook signing secret. */
    webhook_secret_set: boolean
    /**
     * When the settings were last changed.
     * @nullable
     */
    updated_at: string | null
}

/**
 * The run defaults that a profile and the project settings share. A null value sets no default.
 */
export interface PatchedCloudAgentSettingsUpdateApi {
    /**
     * Default GitHub repository, in the format `owner/name`. Null sets no default.
     * @maxLength 255
     * @nullable
     * @pattern ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$
     */
    repository?: string | null
    /**
     * Default base branch. Null uses the default branch of the repository.
     * @maxLength 255
     * @nullable
     */
    branch?: string | null
    /**
     * Default model for the agent. Null lets PostHog select the model.
     * @maxLength 100
     * @nullable
     */
    model?: string | null
    /** Default sandbox size, as `<vCPU>x<memory in GiB>`. Null uses the product default.
     *
     * * `1x2` - 1 vCPU, 2 GiB
     * * `2x4` - 2 vCPU, 4 GiB
     * * `2x8` - 2 vCPU, 8 GiB
     * * `4x8` - 4 vCPU, 8 GiB
     * * `4x16` - 4 vCPU, 16 GiB
     * * `8x16` - 8 vCPU, 16 GiB
     * * `8x32` - 8 vCPU, 32 GiB
     * * `16x64` - 16 vCPU, 64 GiB */
    size?: SizeNameEnumApi | null
    /** How the agent pays for model usage. `auto` uses your own key or subscription when one is connected, and PostHog inference otherwise. Null uses the product default.
     *
     * * `auto` - Auto
     * * `own_key` - Own Key
     * * `own_subscription` - Own Subscription
     * * `posthog` - PostHog */
    inference?: InferenceModeEnumApi | null
    /**
     * Instructions that the agent gets before the prompt. Project instructions come first, then profile instructions, then the instructions of the run.
     * @maxLength 20000
     * @nullable
     */
    instructions?: string | null
    /**
     * Whether the agent opens a pull request when it finishes. Null uses the product default.
     * @nullable
     */
    create_pr?: boolean | null
    /** Whether the pull request opens as a draft or ready for review. Null uses the product default.
     *
     * * `draft` - Draft
     * * `ready` - Ready */
    pr_mode?: PrModeEnumApi | null
    /**
     * The run stops after this many minutes, from 5 to 240. Null uses the product default.
     * @minimum 5
     * @maximum 240
     * @nullable
     */
    max_duration_minutes?: number | null
    /**
     * Cost limit of a run in US dollars. Reserved. Not enforced yet. Null sets no cost limit.
     * @nullable
     * @pattern ^-?\d{0,8}(?:\.\d{0,2})?$
     */
    max_cost_usd?: string | null
    /**
     * ID of the profile that a run uses when it names no profile. Null sets no default profile.
     * @nullable
     */
    default_profile?: string | null
}

/**
 * * `day` - Day
 * * `profile` - Profile
 */
export type UsageGroupByEnumApi = (typeof UsageGroupByEnumApi)[keyof typeof UsageGroupByEnumApi]

export const UsageGroupByEnumApi = {
    Day: 'day',
    Profile: 'profile',
} as const

export interface CloudAgentUsageTotalsApi {
    /** Number of runs. */
    runs: number
    /**
     * Compute cost in US dollars, as a decimal string.
     * @pattern ^-?\d{0,10}(?:\.\d{0,4})?$
     */
    compute_usd: string
    /**
     * Model usage cost in US dollars, as a decimal string. Runs on your own key or subscription add nothing.
     * @pattern ^-?\d{0,10}(?:\.\d{0,4})?$
     */
    inference_usd: string
    /**
     * Sum of the compute cost and the model usage cost, as a decimal string.
     * @pattern ^-?\d{0,10}(?:\.\d{0,4})?$
     */
    total_usd: string
    /**
     * vCPU seconds used.
     * @pattern ^-?\d{0,13}(?:\.\d{0,3})?$
     */
    vcpu_seconds: string
    /**
     * GiB seconds of memory used.
     * @pattern ^-?\d{0,13}(?:\.\d{0,3})?$
     */
    gib_seconds: string
}

export interface CloudAgentUsageBucketApi {
    /**
     * The UTC date of the bucket for `group_by=day`. The profile ID for `group_by=profile`, or null for the runs that used no profile.
     * @nullable
     */
    key: string | null
    /**
     * Name of the profile for `group_by=profile`. Null for other buckets.
     * @nullable
     */
    name: string | null
    /** Usage of the runs in this bucket. */
    usage: CloudAgentUsageTotalsApi
}

export interface CloudAgentUsageSummaryApi {
    /** Start of the range. */
    date_from: string
    /** End of the range, not included. */
    date_to: string
    /** How the buckets are grouped.
     *
     * * `day` - Day
     * * `profile` - Profile */
    group_by: UsageGroupByEnumApi
    /** Usage of all runs created in the range. */
    totals: CloudAgentUsageTotalsApi
    /** Usage for each day or for each profile. */
    buckets: CloudAgentUsageBucketApi[]
}

/**
 * * `run.started` - Run started
 * * `run.completed` - Run completed
 * * `run.failed` - Run failed
 * * `run.cancelled` - Run cancelled
 * * `run.test` - Test event
 */
export type WebhookEventEnumApi = (typeof WebhookEventEnumApi)[keyof typeof WebhookEventEnumApi]

export const WebhookEventEnumApi = {
    Runstarted: 'run.started',
    Runcompleted: 'run.completed',
    Runfailed: 'run.failed',
    Runcancelled: 'run.cancelled',
    Runtest: 'run.test',
} as const

export interface WebhookEndpointApi {
    /** ID of the webhook endpoint. */
    id: string
    /** HTTPS URL that gets a POST request for each event. */
    url: string
    /** Whether PostHog sends events to this endpoint. */
    enabled: boolean
    /**
     * The event types to send. An empty list sends all event types.
     * @maxItems 5
     */
    event_types: WebhookEventEnumApi[]
    /**
     * ID of the user who created the endpoint.
     * @nullable
     */
    created_by: number | null
    /** When the endpoint was created. */
    created_at: string
    /** When the endpoint was last changed. */
    updated_at: string
}

export interface PaginatedWebhookEndpointListApi {
    count: number
    /** @nullable */
    next?: string | null
    /** @nullable */
    previous?: string | null
    results: WebhookEndpointApi[]
}

export interface WebhookEndpointCreateApi {
    /**
     * HTTPS URL that gets a POST request for each event.
     * @maxLength 2000
     */
    url: string
    /** Whether PostHog sends events to this endpoint. */
    enabled?: boolean
    /**
     * The event types to send. An empty list sends all event types.
     * @maxItems 5
     */
    event_types?: WebhookEventEnumApi[]
}

export interface PatchedWebhookEndpointUpdateApi {
    /**
     * HTTPS URL that gets a POST request for each event.
     * @maxLength 2000
     */
    url?: string
    /** Whether PostHog sends events to this endpoint. */
    enabled?: boolean
    /**
     * The event types to send. An empty list sends all event types.
     * @maxItems 5
     */
    event_types?: WebhookEventEnumApi[]
}

export interface WebhookTestApi {
    /** ID of the delivery that carries the test event. */
    delivery_id: string
}

/**
 * * `pending` - Pending
 * * `succeeded` - Succeeded
 * * `failed` - Failed
 * * `gave_up` - Gave Up
 */
export type WebhookDeliveryStatusEnumApi =
    (typeof WebhookDeliveryStatusEnumApi)[keyof typeof WebhookDeliveryStatusEnumApi]

export const WebhookDeliveryStatusEnumApi = {
    Pending: 'pending',
    Succeeded: 'succeeded',
    Failed: 'failed',
    GaveUp: 'gave_up',
} as const

export interface WebhookDeliveryApi {
    /** ID of the delivery. */
    id: string
    /**
     * ID of the webhook endpoint. Null for a delivery to the webhook URL of one run.
     * @nullable
     */
    endpoint: string | null
    /** URL that the event was sent to. */
    url: string
    /** ID of the run that the event is about. */
    run_id: string
    /** Type of the event.
     *
     * * `run.started` - Run started
     * * `run.completed` - Run completed
     * * `run.failed` - Run failed
     * * `run.cancelled` - Run cancelled
     * * `run.test` - Test event */
    event_type: WebhookEventEnumApi
    /** ID of the event. It is the same for every attempt and for every endpoint that gets the event. */
    event_id: string
    /** `pending` waits for an attempt, `succeeded` got a 2xx response, `failed` got a response that a retry cannot fix, and `gave_up` used all its retries.
     *
     * * `pending` - Pending
     * * `succeeded` - Succeeded
     * * `failed` - Failed
     * * `gave_up` - Gave Up */
    status: WebhookDeliveryStatusEnumApi
    /** How many times PostHog tried to send the event. */
    attempts: number
    /**
     * HTTP status of the last attempt. Null when no response arrived.
     * @nullable
     */
    last_status_code: number | null
    /**
     * Kind of connection error of the last attempt. Null when a response arrived.
     * @nullable
     */
    last_error: string | null
    /**
     * When the next attempt is due. Null when no attempt is planned.
     * @nullable
     */
    next_attempt_at: string | null
    /**
     * When the receiver accepted the event.
     * @nullable
     */
    delivered_at: string | null
    /** When the delivery was created. */
    created_at: string
}

export interface WebhookSecretApi {
    /**
     * The signing secret. It is present only in the response that creates or rotates it, so store it then. Null when the project already has a secret: rotate the secret to get a new one.
     * @nullable
     */
    secret: string | null
    /** Whether this request created the secret. */
    created: boolean
}

export type CloudAgentsEstimateRetrieveParams = {
    /**
     * How many minutes the sandbox is up.
     * @minimum 1
     * @maximum 1440
     */
    minutes: number
    /**
     * Sandbox size to price, as `<vCPU>x<memory in GiB>`.
     *
     * * `1x2` - 1 vCPU, 2 GiB
     * * `2x4` - 2 vCPU, 4 GiB
     * * `2x8` - 2 vCPU, 8 GiB
     * * `4x8` - 4 vCPU, 8 GiB
     * * `4x16` - 4 vCPU, 16 GiB
     * * `8x16` - 8 vCPU, 16 GiB
     * * `8x32` - 8 vCPU, 32 GiB
     * * `16x64` - 16 vCPU, 64 GiB
     * @minLength 1
     */
    size: CloudAgentsEstimateRetrieveSize
}

export type CloudAgentsEstimateRetrieveSize =
    (typeof CloudAgentsEstimateRetrieveSize)[keyof typeof CloudAgentsEstimateRetrieveSize]

export const CloudAgentsEstimateRetrieveSize = {
    '1x2': '1x2',
    '2x4': '2x4',
    '2x8': '2x8',
    '4x8': '4x8',
    '4x16': '4x16',
    '8x16': '8x16',
    '8x32': '8x32',
    '16x64': '16x64',
} as const

export type CloudAgentsProfilesListParams = {
    /**
     * Number of results to return per page.
     */
    limit?: number
    /**
     * The initial index from which to return the results.
     */
    offset?: number
}

export type CloudAgentsRunsListParams = {
    /**
     * Return only the runs created at or after this time, in ISO 8601 format.
     */
    created_after?: string
    /**
     * Return only the runs created before this time, in ISO 8601 format.
     */
    created_before?: string
    /**
     * Number of results to return per page.
     */
    limit?: number
    /**
     * The initial index from which to return the results.
     */
    offset?: number
    /**
     * Return only the runs that used this profile.
     */
    profile_id?: string
    /**
     * Return only the runs in this repository, in the format `owner/name`.
     * @minLength 1
     * @maxLength 255
     * @pattern ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$
     */
    repository?: string
    /**
     * Return only the runs with this status.
     *
     * * `queued` - Queued
     * * `running` - Running
     * * `completed` - Completed
     * * `failed` - Failed
     * * `cancelled` - Cancelled
     * @minLength 1
     */
    status?: CloudAgentsRunsListStatus
    /**
     * Return only the runs that have this tag.
     * @minLength 1
     * @maxLength 50
     */
    tag?: string
}

export type CloudAgentsRunsListStatus = (typeof CloudAgentsRunsListStatus)[keyof typeof CloudAgentsRunsListStatus]

export const CloudAgentsRunsListStatus = {
    Queued: 'queued',
    Running: 'running',
    Completed: 'completed',
    Failed: 'failed',
    Cancelled: 'cancelled',
} as const

export type CloudAgentsRunsEventsRetrieveParams = {
    /**
     * `json` returns the stored events as one JSON object, whatever the `Accept` header is.
     */
    format?: CloudAgentsRunsEventsRetrieveFormat
    /**
     * For the event stream: `latest` skips the stored events and sends only new events.
     */
    start?: CloudAgentsRunsEventsRetrieveStart
}

export type CloudAgentsRunsEventsRetrieveFormat =
    (typeof CloudAgentsRunsEventsRetrieveFormat)[keyof typeof CloudAgentsRunsEventsRetrieveFormat]

export const CloudAgentsRunsEventsRetrieveFormat = {
    Json: 'json',
} as const

export type CloudAgentsRunsEventsRetrieveStart =
    (typeof CloudAgentsRunsEventsRetrieveStart)[keyof typeof CloudAgentsRunsEventsRetrieveStart]

export const CloudAgentsRunsEventsRetrieveStart = {
    Latest: 'latest',
} as const

export type CloudAgentsUsageRetrieveParams = {
    /**
     * Start of the range, in ISO 8601 format. The default is 30 days before `date_to`.
     */
    date_from?: string
    /**
     * End of the range, not included, in ISO 8601 format. The default is now.
     */
    date_to?: string
    /**
     * `day` gives one bucket for each UTC day. `profile` gives one bucket for each profile.
     *
     * * `day` - Day
     * * `profile` - Profile
     * @minLength 1
     */
    group_by?: CloudAgentsUsageRetrieveGroupBy
}

export type CloudAgentsUsageRetrieveGroupBy =
    (typeof CloudAgentsUsageRetrieveGroupBy)[keyof typeof CloudAgentsUsageRetrieveGroupBy]

export const CloudAgentsUsageRetrieveGroupBy = {
    Day: 'day',
    Profile: 'profile',
} as const

export type CloudAgentsWebhookEndpointsListParams = {
    /**
     * Number of results to return per page.
     */
    limit?: number
    /**
     * The initial index from which to return the results.
     */
    offset?: number
}
