import * as os from "node:os";
import * as path from "node:path";

export interface MachineClaudeAuth {
  configDir?: string;
  oauthToken?: string;
  /** The run owner's Anthropic API key, for a cloud run that does not use the PostHog gateway. */
  apiKey?: string;
}

/** The env var that tells the Claude CLI which descriptor holds its credential. */
export const CLAUDE_OAUTH_TOKEN_FD_ENV =
  "CLAUDE_CODE_OAUTH_TOKEN_FILE_DESCRIPTOR";
export const CLAUDE_API_KEY_FD_ENV = "CLAUDE_CODE_API_KEY_FILE_DESCRIPTOR";

export interface ClaudeFdCredential {
  secret: string;
  fdEnv: typeof CLAUDE_OAUTH_TOKEN_FD_ENV | typeof CLAUDE_API_KEY_FD_ENV;
}

/**
 * The credential a cloud session hands the Claude CLI on an inherited
 * descriptor. The CLI reads the descriptor once at startup, so the secret is
 * not in its argv, not in its environment, and not in a file. A process that
 * the CLI starts has the same UID and can still read the CLI's memory where
 * the kernel allows it, so this limits exposure and does not remove it.
 */
export function claudeFdCredential(
  auth: MachineClaudeAuth | undefined,
): ClaudeFdCredential | undefined {
  if (auth?.oauthToken) {
    return { secret: auth.oauthToken, fdEnv: CLAUDE_OAUTH_TOKEN_FD_ENV };
  }
  if (auth?.apiKey) {
    return { secret: auth.apiKey, fdEnv: CLAUDE_API_KEY_FD_ENV };
  }
  return undefined;
}

/** Keys that pick the CLI's provider or its endpoint without ANTHROPIC_BASE_URL. */
export const CLAUDE_PROVIDER_ENV_KEYS = [
  "CLAUDE_CODE_USE_BEDROCK",
  "CLAUDE_CODE_USE_VERTEX",
  "CLAUDE_CODE_USE_FOUNDRY",
  "CLAUDE_CODE_USE_ANTHROPIC_AWS",
  "CLAUDE_CODE_USE_ANTHROPIC_GOOGLE_CLOUD",
  "CLAUDE_CODE_USE_MANTLE",
  "CLAUDE_CODE_USE_GATEWAY",
  "ANTHROPIC_BEDROCK_BASE_URL",
  "ANTHROPIC_BEDROCK_MANTLE_BASE_URL",
  "ANTHROPIC_AWS_BASE_URL",
  "ANTHROPIC_VERTEX_BASE_URL",
  "ANTHROPIC_GOOGLE_CLOUD_BASE_URL",
  "ANTHROPIC_FOUNDRY_BASE_URL",
  "AWS_ENDPOINT_URL",
  "AWS_ENDPOINT_URL_BEDROCK",
  "AWS_ENDPOINT_URL_BEDROCK_RUNTIME",
] as const;

/** Keys that route the CLI's connections through another socket or proxy. */
export const CLAUDE_TRANSPORT_ENV_KEYS = [
  "ANTHROPIC_UNIX_SOCKET",
  "HTTP_PROXY",
  "HTTPS_PROXY",
  "ALL_PROXY",
  "http_proxy",
  "https_proxy",
  "all_proxy",
] as const;

export const MACHINE_AUTH_STRIPPED_KEYS = [
  "ANTHROPIC_BASE_URL",
  "ANTHROPIC_AUTH_TOKEN",
  "ANTHROPIC_API_KEY",
  "ANTHROPIC_CUSTOM_HEADERS",
  "OPENAI_BASE_URL",
  "OPENAI_API_KEY",
  ...CLAUDE_PROVIDER_ENV_KEYS,
  "CLAUDE_CODE_ENABLE_TELEMETRY",
  "CLAUDE_CODE_ENHANCED_TELEMETRY_BETA",
  "CLAUDE_CODE_PROPAGATE_TRACEPARENT",
  "OTEL_TRACES_EXPORTER",
  "OTEL_EXPORTER_OTLP_PROTOCOL",
  "OTEL_EXPORTER_OTLP_ENDPOINT",
  "TRACEPARENT",
  "TRACESTATE",
] as const;

let resolvedMachineAuth: MachineClaudeAuth = {};

export const CLOUD_AUTH_STRIPPED_KEYS = [
  ...CLAUDE_TRANSPORT_ENV_KEYS,
  "CLAUDE_CODE_EXECUTABLE",
  "NODE_EXTRA_CA_CERTS",
  "SSL_CERT_FILE",
  "SSL_CERT_DIR",
  "NODE_OPTIONS",
] as const;

export function setMachineClaudeConfigDir(configDir: string | undefined): void {
  resolvedMachineAuth = configDir ? { configDir } : {};
}

export function machineClaudeAuth(): MachineClaudeAuth {
  return resolvedMachineAuth;
}

export function applyMachineClaudeAuth(
  env: Record<string, string | undefined>,
  auth: MachineClaudeAuth,
): void {
  for (const key of MACHINE_AUTH_STRIPPED_KEYS) {
    delete env[key];
  }
  if (auth.oauthToken || auth.apiKey) {
    for (const key of CLOUD_AUTH_STRIPPED_KEYS) delete env[key];
    env.NODE_TLS_REJECT_UNAUTHORIZED = "1";
    delete env.CLAUDE_CODE_OAUTH_TOKEN;
    delete env.CLAUDE_CODE_REMOTE;
    env.CLAUDE_CODE_SUBPROCESS_ENV_SCRUB = "0";
  }
  if (auth.configDir) {
    env.CLAUDE_CONFIG_DIR = auth.configDir;
  } else {
    env.CLAUDE_CONFIG_DIR = path.join(os.homedir(), ".claude");
  }
}

export function machineClaudeAuthShellEnv(auth: MachineClaudeAuth): {
  set: Record<string, string>;
  unset: string[];
} {
  const unset: string[] = [
    ...MACHINE_AUTH_STRIPPED_KEYS,
    "CLAUDE_CODE_OAUTH_TOKEN",
    CLAUDE_OAUTH_TOKEN_FD_ENV,
    CLAUDE_API_KEY_FD_ENV,
  ];
  if (auth.configDir) {
    return { set: { CLAUDE_CONFIG_DIR: auth.configDir }, unset };
  }
  return {
    set: { CLAUDE_CONFIG_DIR: path.join(os.homedir(), ".claude") },
    unset,
  };
}
