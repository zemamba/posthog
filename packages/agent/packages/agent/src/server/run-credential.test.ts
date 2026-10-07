import { describe, expect, it, vi } from "vitest";
import { RunCredentialError } from "../posthog-api";
import {
  RunCredentialClient,
  runCredentialFailureMessage,
} from "./run-credential";

function createClient() {
  const requestStoredRunCredential = vi.fn();
  const info = vi.fn();
  const client = new RunCredentialClient({
    posthogAPI: { requestStoredRunCredential },
    taskId: "task-1",
    runId: "run-1",
    runToken: "run-token",
    logger: { info } as never,
  });
  return { client, requestStoredRunCredential, info };
}

describe("RunCredentialClient", () => {
  it("fetches a credential once with the run token and never logs the secret", async () => {
    const { client, requestStoredRunCredential, info } = createClient();
    requestStoredRunCredential.mockResolvedValue("sk-ant-api03-fake");

    const [first, second] = await Promise.all([
      client.get("anthropic_api_key"),
      client.get("anthropic_api_key"),
    ]);
    const third = await client.get("anthropic_api_key");

    expect([first, second, third]).toEqual([
      "sk-ant-api03-fake",
      "sk-ant-api03-fake",
      "sk-ant-api03-fake",
    ]);
    expect(requestStoredRunCredential).toHaveBeenCalledTimes(1);
    expect(requestStoredRunCredential).toHaveBeenCalledWith(
      "task-1",
      "run-1",
      "run-token",
      "anthropic_api_key",
      expect.any(Number),
    );
    expect(JSON.stringify(info.mock.calls)).not.toContain("sk-ant-api03-fake");
  });

  it("asks again after a failed request", async () => {
    const { client, requestStoredRunCredential } = createClient();
    requestStoredRunCredential
      .mockRejectedValueOnce(
        new RunCredentialError("openai_api_key", "request_failed", 500, "x"),
      )
      .mockResolvedValueOnce("sk-fake-openai");

    await expect(client.get("openai_api_key")).rejects.toMatchObject({
      code: "request_failed",
    });
    await expect(client.get("openai_api_key")).resolves.toBe("sk-fake-openai");
  });

  it.each([
    [
      "anthropic_api_key",
      "credential_missing",
      "Add your Anthropic API key in Cloud agents settings, then start the run again.",
    ],
    [
      "claude_subscription",
      "credential_missing",
      "Add your Claude subscription in Cloud agents settings, then start the run again.",
    ],
    [
      "openai_api_key",
      "forbidden",
      "This run could not get your OpenAI API key from PostHog. Start the run again.",
    ],
  ] as const)(
    "explains a %s request that failed with %s",
    (credential, code, message) => {
      expect(
        runCredentialFailureMessage(
          credential,
          new RunCredentialError(credential, code, 404, "x"),
        ),
      ).toBe(message);
    },
  );
});
