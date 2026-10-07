import { CodeSnippet, Language } from 'lib/components/CodeSnippet'

const VERIFY_SNIPPET = `import hashlib
import hmac

def is_from_posthog(secret: str, headers: dict, body: bytes) -> bool:
    timestamp = headers["X-PostHog-Webhook-Timestamp"]
    signature = headers["X-PostHog-Webhook-Signature"]  # v1=<hex>
    expected = hmac.new(
        secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(signature, f"v1={expected}")`

export function WebhookSignatureSnippet(): JSX.Element {
    return (
        <div className="flex max-w-180 min-w-0 flex-col gap-2">
            <h3 className="m-0 text-base font-semibold">Verify the signature</h3>
            <p className="m-0 text-secondary">
                Each request has the headers <code>X-PostHog-Webhook-Timestamp</code> and{' '}
                <code>X-PostHog-Webhook-Signature: v1=&lt;hex&gt;</code>. The signature is the HMAC-SHA256 of{' '}
                <code>{'{timestamp}.{body}'}</code> with your signing secret. Compute it over the raw request body, and
                reject a request when the two do not match or the timestamp is old.
            </p>
            <CodeSnippet language={Language.Python} thing="snippet">
                {VERIFY_SNIPPET}
            </CodeSnippet>
        </div>
    )
}
