/**
 * Auto-generated Zod validation schemas from the Django backend OpenAPI schema.
 * To modify these schemas, update the Django serializers or views, then run:
 *   hogli build:openapi
 * Questions or issues? #team-devex on Slack
 *
 * PostHog API - generated
 * OpenAPI spec version: 1.0.0
 */
import * as zod from 'zod'

/**
 * A profile is a named set of run defaults. A run names a profile to use its defaults.
 * @summary Create a profile
 */
export const cloudAgentsProfilesCreateBodyRepositoryMax = 255

export const cloudAgentsProfilesCreateBodyRepositoryRegExp = new RegExp('^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$')
export const cloudAgentsProfilesCreateBodyBranchMax = 255

export const cloudAgentsProfilesCreateBodyModelMax = 100

export const cloudAgentsProfilesCreateBodyInstructionsMax = 20000

export const cloudAgentsProfilesCreateBodyMaxDurationMinutesMin = 5
export const cloudAgentsProfilesCreateBodyMaxDurationMinutesMax = 240

export const cloudAgentsProfilesCreateBodyMaxCostUsdRegExp = new RegExp('^-?\\d{0,8}(?:\\.\\d{0,2})?$')
export const cloudAgentsProfilesCreateBodyDescriptionMax = 2000

export const cloudAgentsProfilesCreateBodyTagsItemMax = 50

export const cloudAgentsProfilesCreateBodyTagsMax = 20

export const cloudAgentsProfilesCreateBodyWebhookUrlMax = 2000

export const cloudAgentsProfilesCreateBodyNameMax = 100

export const CloudAgentsProfilesCreateBody = /* @__PURE__ */ zod
    .object({
        repository: zod
            .string()
            .max(cloudAgentsProfilesCreateBodyRepositoryMax)
            .regex(cloudAgentsProfilesCreateBodyRepositoryRegExp)
            .nullish()
            .describe('Default GitHub repository, in the format `owner\/name`. Null sets no default.'),
        branch: zod
            .string()
            .max(cloudAgentsProfilesCreateBodyBranchMax)
            .nullish()
            .describe('Default base branch. Null uses the default branch of the repository.'),
        model: zod
            .string()
            .max(cloudAgentsProfilesCreateBodyModelMax)
            .nullish()
            .describe('Default model for the agent. Null lets PostHog select the model.'),
        size: zod
            .union([
                zod
                    .enum(['1x2', '2x4', '2x8', '4x8', '4x16', '8x16', '8x32', '16x64'])
                    .describe(
                        '\* `1x2` - 1 vCPU, 2 GiB\n\* `2x4` - 2 vCPU, 4 GiB\n\* `2x8` - 2 vCPU, 8 GiB\n\* `4x8` - 4 vCPU, 8 GiB\n\* `4x16` - 4 vCPU, 16 GiB\n\* `8x16` - 8 vCPU, 16 GiB\n\* `8x32` - 8 vCPU, 32 GiB\n\* `16x64` - 16 vCPU, 64 GiB'
                    ),
                zod.null(),
            ])
            .optional()
            .describe(
                'Default sandbox size, as `<vCPU>x<memory in GiB>`. Null uses the product default.\n\n\* `1x2` - 1 vCPU, 2 GiB\n\* `2x4` - 2 vCPU, 4 GiB\n\* `2x8` - 2 vCPU, 8 GiB\n\* `4x8` - 4 vCPU, 8 GiB\n\* `4x16` - 4 vCPU, 16 GiB\n\* `8x16` - 8 vCPU, 16 GiB\n\* `8x32` - 8 vCPU, 32 GiB\n\* `16x64` - 16 vCPU, 64 GiB'
            ),
        inference: zod
            .union([
                zod
                    .enum(['auto', 'own_key', 'own_subscription', 'posthog'])
                    .describe(
                        '\* `auto` - Auto\n\* `own_key` - Own Key\n\* `own_subscription` - Own Subscription\n\* `posthog` - PostHog'
                    ),
                zod.null(),
            ])
            .optional()
            .describe(
                'How the agent pays for model usage. `auto` uses your own key or subscription when one is connected, and PostHog inference otherwise. Null uses the product default.\n\n\* `auto` - Auto\n\* `own_key` - Own Key\n\* `own_subscription` - Own Subscription\n\* `posthog` - PostHog'
            ),
        instructions: zod
            .string()
            .max(cloudAgentsProfilesCreateBodyInstructionsMax)
            .nullish()
            .describe(
                'Instructions that the agent gets before the prompt. Project instructions come first, then profile instructions, then the instructions of the run.'
            ),
        create_pr: zod
            .boolean()
            .nullish()
            .describe('Whether the agent opens a pull request when it finishes. Null uses the product default.'),
        pr_mode: zod
            .union([zod.enum(['draft', 'ready']).describe('\* `draft` - Draft\n\* `ready` - Ready'), zod.null()])
            .optional()
            .describe(
                'Whether the pull request opens as a draft or ready for review. Null uses the product default.\n\n\* `draft` - Draft\n\* `ready` - Ready'
            ),
        max_duration_minutes: zod
            .number()
            .min(cloudAgentsProfilesCreateBodyMaxDurationMinutesMin)
            .max(cloudAgentsProfilesCreateBodyMaxDurationMinutesMax)
            .nullish()
            .describe('The run stops after this many minutes, from 5 to 240. Null uses the product default.'),
        max_cost_usd: zod
            .stringFormat('decimal', cloudAgentsProfilesCreateBodyMaxCostUsdRegExp)
            .nullish()
            .describe('Cost limit of a run in US dollars. Reserved. Not enforced yet. Null sets no cost limit.'),
        description: zod
            .string()
            .max(cloudAgentsProfilesCreateBodyDescriptionMax)
            .optional()
            .describe('What this profile is for.'),
        tags: zod
            .array(zod.string().max(cloudAgentsProfilesCreateBodyTagsItemMax))
            .max(cloudAgentsProfilesCreateBodyTagsMax)
            .optional()
            .describe('Tags added to every run that uses this profile.'),
        webhook_url: zod
            .url()
            .max(cloudAgentsProfilesCreateBodyWebhookUrlMax)
            .nullish()
            .describe('HTTPS URL that gets the events of every run that uses this profile. Null sends none.'),
        name: zod
            .string()
            .max(cloudAgentsProfilesCreateBodyNameMax)
            .describe('Name of the profile. It is unique in the project, without regard to case.'),
    })
    .describe('The run defaults that a profile and the project settings share. A null value sets no default.')

/**
 * Only the fields in the request change. A null value clears a default.
 * @summary Update a profile
 */
export const cloudAgentsProfilesPartialUpdateBodyRepositoryMax = 255

export const cloudAgentsProfilesPartialUpdateBodyRepositoryRegExp = new RegExp('^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$')
export const cloudAgentsProfilesPartialUpdateBodyBranchMax = 255

export const cloudAgentsProfilesPartialUpdateBodyModelMax = 100

export const cloudAgentsProfilesPartialUpdateBodyInstructionsMax = 20000

export const cloudAgentsProfilesPartialUpdateBodyMaxDurationMinutesMin = 5
export const cloudAgentsProfilesPartialUpdateBodyMaxDurationMinutesMax = 240

export const cloudAgentsProfilesPartialUpdateBodyMaxCostUsdRegExp = new RegExp('^-?\\d{0,8}(?:\\.\\d{0,2})?$')
export const cloudAgentsProfilesPartialUpdateBodyDescriptionMax = 2000

export const cloudAgentsProfilesPartialUpdateBodyTagsItemMax = 50

export const cloudAgentsProfilesPartialUpdateBodyTagsMax = 20

export const cloudAgentsProfilesPartialUpdateBodyWebhookUrlMax = 2000

export const cloudAgentsProfilesPartialUpdateBodyNameMax = 100

export const CloudAgentsProfilesPartialUpdateBody = /* @__PURE__ */ zod
    .object({
        repository: zod
            .string()
            .max(cloudAgentsProfilesPartialUpdateBodyRepositoryMax)
            .regex(cloudAgentsProfilesPartialUpdateBodyRepositoryRegExp)
            .nullish()
            .describe('Default GitHub repository, in the format `owner\/name`. Null sets no default.'),
        branch: zod
            .string()
            .max(cloudAgentsProfilesPartialUpdateBodyBranchMax)
            .nullish()
            .describe('Default base branch. Null uses the default branch of the repository.'),
        model: zod
            .string()
            .max(cloudAgentsProfilesPartialUpdateBodyModelMax)
            .nullish()
            .describe('Default model for the agent. Null lets PostHog select the model.'),
        size: zod
            .union([
                zod
                    .enum(['1x2', '2x4', '2x8', '4x8', '4x16', '8x16', '8x32', '16x64'])
                    .describe(
                        '\* `1x2` - 1 vCPU, 2 GiB\n\* `2x4` - 2 vCPU, 4 GiB\n\* `2x8` - 2 vCPU, 8 GiB\n\* `4x8` - 4 vCPU, 8 GiB\n\* `4x16` - 4 vCPU, 16 GiB\n\* `8x16` - 8 vCPU, 16 GiB\n\* `8x32` - 8 vCPU, 32 GiB\n\* `16x64` - 16 vCPU, 64 GiB'
                    ),
                zod.null(),
            ])
            .optional()
            .describe(
                'Default sandbox size, as `<vCPU>x<memory in GiB>`. Null uses the product default.\n\n\* `1x2` - 1 vCPU, 2 GiB\n\* `2x4` - 2 vCPU, 4 GiB\n\* `2x8` - 2 vCPU, 8 GiB\n\* `4x8` - 4 vCPU, 8 GiB\n\* `4x16` - 4 vCPU, 16 GiB\n\* `8x16` - 8 vCPU, 16 GiB\n\* `8x32` - 8 vCPU, 32 GiB\n\* `16x64` - 16 vCPU, 64 GiB'
            ),
        inference: zod
            .union([
                zod
                    .enum(['auto', 'own_key', 'own_subscription', 'posthog'])
                    .describe(
                        '\* `auto` - Auto\n\* `own_key` - Own Key\n\* `own_subscription` - Own Subscription\n\* `posthog` - PostHog'
                    ),
                zod.null(),
            ])
            .optional()
            .describe(
                'How the agent pays for model usage. `auto` uses your own key or subscription when one is connected, and PostHog inference otherwise. Null uses the product default.\n\n\* `auto` - Auto\n\* `own_key` - Own Key\n\* `own_subscription` - Own Subscription\n\* `posthog` - PostHog'
            ),
        instructions: zod
            .string()
            .max(cloudAgentsProfilesPartialUpdateBodyInstructionsMax)
            .nullish()
            .describe(
                'Instructions that the agent gets before the prompt. Project instructions come first, then profile instructions, then the instructions of the run.'
            ),
        create_pr: zod
            .boolean()
            .nullish()
            .describe('Whether the agent opens a pull request when it finishes. Null uses the product default.'),
        pr_mode: zod
            .union([zod.enum(['draft', 'ready']).describe('\* `draft` - Draft\n\* `ready` - Ready'), zod.null()])
            .optional()
            .describe(
                'Whether the pull request opens as a draft or ready for review. Null uses the product default.\n\n\* `draft` - Draft\n\* `ready` - Ready'
            ),
        max_duration_minutes: zod
            .number()
            .min(cloudAgentsProfilesPartialUpdateBodyMaxDurationMinutesMin)
            .max(cloudAgentsProfilesPartialUpdateBodyMaxDurationMinutesMax)
            .nullish()
            .describe('The run stops after this many minutes, from 5 to 240. Null uses the product default.'),
        max_cost_usd: zod
            .stringFormat('decimal', cloudAgentsProfilesPartialUpdateBodyMaxCostUsdRegExp)
            .nullish()
            .describe('Cost limit of a run in US dollars. Reserved. Not enforced yet. Null sets no cost limit.'),
        description: zod
            .string()
            .max(cloudAgentsProfilesPartialUpdateBodyDescriptionMax)
            .optional()
            .describe('What this profile is for.'),
        tags: zod
            .array(zod.string().max(cloudAgentsProfilesPartialUpdateBodyTagsItemMax))
            .max(cloudAgentsProfilesPartialUpdateBodyTagsMax)
            .optional()
            .describe('Tags added to every run that uses this profile.'),
        webhook_url: zod
            .url()
            .max(cloudAgentsProfilesPartialUpdateBodyWebhookUrlMax)
            .nullish()
            .describe('HTTPS URL that gets the events of every run that uses this profile. Null sends none.'),
        name: zod
            .string()
            .max(cloudAgentsProfilesPartialUpdateBodyNameMax)
            .optional()
            .describe('Name of the profile. It is unique in the project, without regard to case.'),
    })
    .describe('The run defaults that a profile and the project settings share. A null value sets no default.')

/**
 * Starts a sandbox with a coding agent that works on the prompt in the repository. The response returns at once with a `queued` run. Read the run, stream its events or register a webhook to follow it. Send the same `Idempotency-Key` header again to get the same run and not a second one.
 * @summary Start a run
 */
export const cloudAgentsRunsCreateBodyRepositoryMax = 255

export const cloudAgentsRunsCreateBodyRepositoryRegExp = new RegExp('^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$')
export const cloudAgentsRunsCreateBodyBranchMax = 255

export const cloudAgentsRunsCreateBodyModelMax = 100

export const cloudAgentsRunsCreateBodyInstructionsMax = 20000

export const cloudAgentsRunsCreateBodyMaxDurationMinutesMin = 5
export const cloudAgentsRunsCreateBodyMaxDurationMinutesMax = 240

export const cloudAgentsRunsCreateBodyMaxCostUsdRegExp = new RegExp('^-?\\d{0,8}(?:\\.\\d{0,2})?$')
export const cloudAgentsRunsCreateBodyPromptMax = 64000

export const cloudAgentsRunsCreateBodyProfileMax = 100

export const cloudAgentsRunsCreateBodyTagsItemMax = 50

export const cloudAgentsRunsCreateBodyTagsMax = 20

export const cloudAgentsRunsCreateBodyMetadataMaxOne = 512

export const cloudAgentsRunsCreateBodyWebhookUrlMax = 2000

export const CloudAgentsRunsCreateBody = /* @__PURE__ */ zod
    .object({
        repository: zod
            .string()
            .max(cloudAgentsRunsCreateBodyRepositoryMax)
            .regex(cloudAgentsRunsCreateBodyRepositoryRegExp)
            .nullish()
            .describe(
                'GitHub repository that the agent works in, in the format `owner\/name`. Required unless the profile or the project settings set a default.'
            ),
        branch: zod
            .string()
            .max(cloudAgentsRunsCreateBodyBranchMax)
            .nullish()
            .describe('Default base branch. Null uses the default branch of the repository.'),
        model: zod
            .string()
            .max(cloudAgentsRunsCreateBodyModelMax)
            .nullish()
            .describe('Default model for the agent. Null lets PostHog select the model.'),
        size: zod
            .union([
                zod
                    .enum(['1x2', '2x4', '2x8', '4x8', '4x16', '8x16', '8x32', '16x64'])
                    .describe(
                        '\* `1x2` - 1 vCPU, 2 GiB\n\* `2x4` - 2 vCPU, 4 GiB\n\* `2x8` - 2 vCPU, 8 GiB\n\* `4x8` - 4 vCPU, 8 GiB\n\* `4x16` - 4 vCPU, 16 GiB\n\* `8x16` - 8 vCPU, 16 GiB\n\* `8x32` - 8 vCPU, 32 GiB\n\* `16x64` - 16 vCPU, 64 GiB'
                    ),
                zod.null(),
            ])
            .optional()
            .describe(
                'Default sandbox size, as `<vCPU>x<memory in GiB>`. Null uses the product default.\n\n\* `1x2` - 1 vCPU, 2 GiB\n\* `2x4` - 2 vCPU, 4 GiB\n\* `2x8` - 2 vCPU, 8 GiB\n\* `4x8` - 4 vCPU, 8 GiB\n\* `4x16` - 4 vCPU, 16 GiB\n\* `8x16` - 8 vCPU, 16 GiB\n\* `8x32` - 8 vCPU, 32 GiB\n\* `16x64` - 16 vCPU, 64 GiB'
            ),
        inference: zod
            .union([
                zod
                    .enum(['auto', 'own_key', 'own_subscription', 'posthog'])
                    .describe(
                        '\* `auto` - Auto\n\* `own_key` - Own Key\n\* `own_subscription` - Own Subscription\n\* `posthog` - PostHog'
                    ),
                zod.null(),
            ])
            .optional()
            .describe(
                'How the agent pays for model usage. `auto` uses your own key or subscription when one is connected, and PostHog inference otherwise. Null uses the product default.\n\n\* `auto` - Auto\n\* `own_key` - Own Key\n\* `own_subscription` - Own Subscription\n\* `posthog` - PostHog'
            ),
        instructions: zod
            .string()
            .max(cloudAgentsRunsCreateBodyInstructionsMax)
            .nullish()
            .describe(
                'Instructions that the agent gets before the prompt. Project instructions come first, then profile instructions, then the instructions of the run.'
            ),
        create_pr: zod
            .boolean()
            .nullish()
            .describe('Whether the agent opens a pull request when it finishes. Null uses the product default.'),
        pr_mode: zod
            .union([zod.enum(['draft', 'ready']).describe('\* `draft` - Draft\n\* `ready` - Ready'), zod.null()])
            .optional()
            .describe(
                'Whether the pull request opens as a draft or ready for review. Null uses the product default.\n\n\* `draft` - Draft\n\* `ready` - Ready'
            ),
        max_duration_minutes: zod
            .number()
            .min(cloudAgentsRunsCreateBodyMaxDurationMinutesMin)
            .max(cloudAgentsRunsCreateBodyMaxDurationMinutesMax)
            .nullish()
            .describe('The run stops after this many minutes, from 5 to 240. Null uses the product default.'),
        max_cost_usd: zod
            .stringFormat('decimal', cloudAgentsRunsCreateBodyMaxCostUsdRegExp)
            .nullish()
            .describe('Cost limit of a run in US dollars. Reserved. Not enforced yet. Null sets no cost limit.'),
        prompt: zod
            .string()
            .max(cloudAgentsRunsCreateBodyPromptMax)
            .describe('The task for the agent, in plain language.'),
        profile: zod
            .string()
            .max(cloudAgentsRunsCreateBodyProfileMax)
            .nullish()
            .describe(
                'ID or name of the profile whose defaults the run uses. Null uses the default profile of the project, when one is set.'
            ),
        tags: zod
            .array(zod.string().max(cloudAgentsRunsCreateBodyTagsItemMax))
            .max(cloudAgentsRunsCreateBodyTagsMax)
            .optional()
            .describe('Tags for the run. The tags of the profile are added to them.'),
        metadata: zod
            .record(zod.string(), zod.string().max(cloudAgentsRunsCreateBodyMetadataMaxOne))
            .optional()
            .describe(
                'Your own key and value pairs, stored with the run and returned with it. At most 16 pairs. Keys and values are strings.'
            ),
        webhook_url: zod
            .url()
            .max(cloudAgentsRunsCreateBodyWebhookUrlMax)
            .nullish()
            .describe(
                'HTTPS URL that gets the events of this run, in addition to the webhook endpoints of the project.'
            ),
    })
    .describe('The run defaults that a profile and the project settings share. A null value sets no default.')

/**
 * Sends a follow-up message. An agent that is at work gets the message in its current session. A run that stopped starts a new agent session with the message and goes back to `queued`.
 * @summary Send a message to a run
 */
export const cloudAgentsRunsMessagesCreateBodyContentMax = 64000

export const CloudAgentsRunsMessagesCreateBody = /* @__PURE__ */ zod.object({
    content: zod
        .string()
        .max(cloudAgentsRunsMessagesCreateBodyContentMax)
        .describe('The follow-up message for the agent, in plain language.'),
})

/**
 * Only the fields in the request change. A null value clears a default.
 * @summary Update cloud agent settings
 */
export const cloudAgentsSettingsPartialUpdateBodyRepositoryMax = 255

export const cloudAgentsSettingsPartialUpdateBodyRepositoryRegExp = new RegExp('^[A-Za-z0-9_.-]+\/[A-Za-z0-9_.-]+$')
export const cloudAgentsSettingsPartialUpdateBodyBranchMax = 255

export const cloudAgentsSettingsPartialUpdateBodyModelMax = 100

export const cloudAgentsSettingsPartialUpdateBodyInstructionsMax = 20000

export const cloudAgentsSettingsPartialUpdateBodyMaxDurationMinutesMin = 5
export const cloudAgentsSettingsPartialUpdateBodyMaxDurationMinutesMax = 240

export const cloudAgentsSettingsPartialUpdateBodyMaxCostUsdRegExp = new RegExp('^-?\\d{0,8}(?:\\.\\d{0,2})?$')

export const CloudAgentsSettingsPartialUpdateBody = /* @__PURE__ */ zod
    .object({
        repository: zod
            .string()
            .max(cloudAgentsSettingsPartialUpdateBodyRepositoryMax)
            .regex(cloudAgentsSettingsPartialUpdateBodyRepositoryRegExp)
            .nullish()
            .describe('Default GitHub repository, in the format `owner\/name`. Null sets no default.'),
        branch: zod
            .string()
            .max(cloudAgentsSettingsPartialUpdateBodyBranchMax)
            .nullish()
            .describe('Default base branch. Null uses the default branch of the repository.'),
        model: zod
            .string()
            .max(cloudAgentsSettingsPartialUpdateBodyModelMax)
            .nullish()
            .describe('Default model for the agent. Null lets PostHog select the model.'),
        size: zod
            .union([
                zod
                    .enum(['1x2', '2x4', '2x8', '4x8', '4x16', '8x16', '8x32', '16x64'])
                    .describe(
                        '\* `1x2` - 1 vCPU, 2 GiB\n\* `2x4` - 2 vCPU, 4 GiB\n\* `2x8` - 2 vCPU, 8 GiB\n\* `4x8` - 4 vCPU, 8 GiB\n\* `4x16` - 4 vCPU, 16 GiB\n\* `8x16` - 8 vCPU, 16 GiB\n\* `8x32` - 8 vCPU, 32 GiB\n\* `16x64` - 16 vCPU, 64 GiB'
                    ),
                zod.null(),
            ])
            .optional()
            .describe(
                'Default sandbox size, as `<vCPU>x<memory in GiB>`. Null uses the product default.\n\n\* `1x2` - 1 vCPU, 2 GiB\n\* `2x4` - 2 vCPU, 4 GiB\n\* `2x8` - 2 vCPU, 8 GiB\n\* `4x8` - 4 vCPU, 8 GiB\n\* `4x16` - 4 vCPU, 16 GiB\n\* `8x16` - 8 vCPU, 16 GiB\n\* `8x32` - 8 vCPU, 32 GiB\n\* `16x64` - 16 vCPU, 64 GiB'
            ),
        inference: zod
            .union([
                zod
                    .enum(['auto', 'own_key', 'own_subscription', 'posthog'])
                    .describe(
                        '\* `auto` - Auto\n\* `own_key` - Own Key\n\* `own_subscription` - Own Subscription\n\* `posthog` - PostHog'
                    ),
                zod.null(),
            ])
            .optional()
            .describe(
                'How the agent pays for model usage. `auto` uses your own key or subscription when one is connected, and PostHog inference otherwise. Null uses the product default.\n\n\* `auto` - Auto\n\* `own_key` - Own Key\n\* `own_subscription` - Own Subscription\n\* `posthog` - PostHog'
            ),
        instructions: zod
            .string()
            .max(cloudAgentsSettingsPartialUpdateBodyInstructionsMax)
            .nullish()
            .describe(
                'Instructions that the agent gets before the prompt. Project instructions come first, then profile instructions, then the instructions of the run.'
            ),
        create_pr: zod
            .boolean()
            .nullish()
            .describe('Whether the agent opens a pull request when it finishes. Null uses the product default.'),
        pr_mode: zod
            .union([zod.enum(['draft', 'ready']).describe('\* `draft` - Draft\n\* `ready` - Ready'), zod.null()])
            .optional()
            .describe(
                'Whether the pull request opens as a draft or ready for review. Null uses the product default.\n\n\* `draft` - Draft\n\* `ready` - Ready'
            ),
        max_duration_minutes: zod
            .number()
            .min(cloudAgentsSettingsPartialUpdateBodyMaxDurationMinutesMin)
            .max(cloudAgentsSettingsPartialUpdateBodyMaxDurationMinutesMax)
            .nullish()
            .describe('The run stops after this many minutes, from 5 to 240. Null uses the product default.'),
        max_cost_usd: zod
            .stringFormat('decimal', cloudAgentsSettingsPartialUpdateBodyMaxCostUsdRegExp)
            .nullish()
            .describe('Cost limit of a run in US dollars. Reserved. Not enforced yet. Null sets no cost limit.'),
        default_profile: zod
            .uuid()
            .nullish()
            .describe('ID of the profile that a run uses when it names no profile. Null sets no default profile.'),
    })
    .describe('The run defaults that a profile and the project settings share. A null value sets no default.')

/**
 * PostHog sends run events to the URL as signed POST requests. A project can have 5 endpoints.
 * @summary Create a webhook endpoint
 */
export const cloudAgentsWebhookEndpointsCreateBodyUrlMax = 2000

export const cloudAgentsWebhookEndpointsCreateBodyEnabledDefault = true
export const cloudAgentsWebhookEndpointsCreateBodyEventTypesMax = 5

export const CloudAgentsWebhookEndpointsCreateBody = /* @__PURE__ */ zod.object({
    url: zod
        .url()
        .max(cloudAgentsWebhookEndpointsCreateBodyUrlMax)
        .describe('HTTPS URL that gets a POST request for each event.'),
    enabled: zod
        .boolean()
        .default(cloudAgentsWebhookEndpointsCreateBodyEnabledDefault)
        .describe('Whether PostHog sends events to this endpoint.'),
    event_types: zod
        .array(
            zod
                .enum(['run.started', 'run.completed', 'run.failed', 'run.cancelled', 'run.test'])
                .describe(
                    '\* `run.started` - Run started\n\* `run.completed` - Run completed\n\* `run.failed` - Run failed\n\* `run.cancelled` - Run cancelled\n\* `run.test` - Test event'
                )
        )
        .max(cloudAgentsWebhookEndpointsCreateBodyEventTypesMax)
        .optional()
        .describe('The event types to send. An empty list sends all event types.'),
})

/**
 * Base for every cloud_agents viewset: the scope object, the feature flag, and the error mapping.
 * @summary Update a webhook endpoint
 */
export const cloudAgentsWebhookEndpointsPartialUpdateBodyUrlMax = 2000

export const cloudAgentsWebhookEndpointsPartialUpdateBodyEventTypesMax = 5

export const CloudAgentsWebhookEndpointsPartialUpdateBody = /* @__PURE__ */ zod.object({
    url: zod
        .url()
        .max(cloudAgentsWebhookEndpointsPartialUpdateBodyUrlMax)
        .optional()
        .describe('HTTPS URL that gets a POST request for each event.'),
    enabled: zod.boolean().optional().describe('Whether PostHog sends events to this endpoint.'),
    event_types: zod
        .array(
            zod
                .enum(['run.started', 'run.completed', 'run.failed', 'run.cancelled', 'run.test'])
                .describe(
                    '\* `run.started` - Run started\n\* `run.completed` - Run completed\n\* `run.failed` - Run failed\n\* `run.cancelled` - Run cancelled\n\* `run.test` - Test event'
                )
        )
        .max(cloudAgentsWebhookEndpointsPartialUpdateBodyEventTypesMax)
        .optional()
        .describe('The event types to send. An empty list sends all event types.'),
})
