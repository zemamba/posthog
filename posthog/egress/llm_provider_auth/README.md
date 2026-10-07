# LLM provider auth egress

Calls that check a user's own Anthropic or OpenAI API key before PostHog stores it for cloud agent runs.

## Identity

The provider name: `anthropic` or `openai`.
The budget owner at the provider is the user's own account, and the only id PostHog holds for that account is the key.
A key, or a digest of a key, must never become a metric label, so the scope stops at the provider.

## Budget

None: calls are recorded, never gated (`RecordedEgressClient`).
The credential belongs to the user's account at the provider, and no PostHog-owned credential shares its limit.
PostHog sends one request each time a user saves a key.
The route that saves a key has a per-user throttle (`InferenceCredentialConnectUserThrottle` in `posthog/rate_limit.py`), which bounds the request volume.

## Lanes and callers

No lanes, because nothing is gated.
`posthog/models/integration/inference_credentials.py` is the caller.
It sends one `GET` to the provider's model list when a user saves an API key, and it reads only the status code.
A `200` means the key works.
A `401` or a `403` means the provider does not accept the key, and PostHog does not store it.
Any other outcome means the key could not be checked, and PostHog does not store it.

A Claude subscription token is not checked against the provider, because no documented endpoint accepts it for a check.

## Rate-limit headers

None parsed, so the domain declares no gauges.
The counter is `llm_provider_auth_api_requests_total`, labeled `scope, method, endpoint, status_code, source`.

## Auth

The key the user submits.
Anthropic takes it in the `x-api-key` header with an `anthropic-version` header.
OpenAI takes it in the `Authorization: Bearer` header.
No PostHog-owned credential.

## Sources

- [Anthropic: List models](https://platform.claude.com/docs/en/api/models/list): `GET https://api.anthropic.com/v1/models` takes an optional `limit` query parameter, and the example sends `anthropic-version: 2023-06-01` and `X-Api-Key`.
- [Anthropic: Errors](https://platform.claude.com/docs/en/api/errors): `401 authentication_error` means a problem with the API key, and `403 permission_error` means the key has no permission for the resource.
- [OpenAI: List models](https://developers.openai.com/api/reference/resources/models/methods/list): `GET https://api.openai.com/v1/models` with `Authorization: Bearer $OPENAI_API_KEY`.
- [OpenAI: Error codes](https://developers.openai.com/api/docs/guides/error-codes): `401` covers an incorrect key, a key outside its organization, and a request from an IP address outside the allowlist. The only documented `403` is an unsupported country or region. Unverified: the status code OpenAI returns for a restricted key that has no permission to list models.
