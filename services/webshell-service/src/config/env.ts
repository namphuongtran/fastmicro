/**
 * Environment configuration with runtime validation.
 *
 * Uses Zod to validate environment variables at startup,
 * ensuring all required configuration is present and valid.
 *
 * @module config/env
 */

import { z } from "zod";

/**
 * Server-side environment variables schema.
 * These are only available on the server.
 */
const serverEnvSchema = z.object({
  // Identity Service
  IDENTITY_SERVICE_URL: z
    .string()
    .url()
    .default("http://localhost:8003"),
  OAUTH_CLIENT_ID: z
    .string()
    .min(1)
    .default("webshell-frontend"),
  NEXTAUTH_URL: z
    .string()
    .url()
    .default("http://localhost:3000"),
  NEXTAUTH_SECRET: z
    .string()
    .min(32)
    .optional(), // Required in production

  // Node environment
  NODE_ENV: z
    .enum(["development", "test", "production"])
    .default("development"),
});

/**
 * Client-side environment variables schema.
 * These are exposed to the browser (prefixed with NEXT_PUBLIC_).
 */
const clientEnvSchema = z.object({
  // API Gateway
  NEXT_PUBLIC_API_URL: z
    .string()
    .url()
    .default("http://localhost:8000"),

  // Multi-tenancy
  NEXT_PUBLIC_DEFAULT_TENANT_ID: z
    .string()
    .optional()
    .default("default"),

  // Feature flags
  NEXT_PUBLIC_FEATURE_FLAGS_ENABLED: z
    .string()
    .transform((val) => val === "true")
    .default(false),

  // Observability
  NEXT_PUBLIC_LOG_LEVEL: z
    .enum(["debug", "info", "warn", "error"])
    .default("info"),

  // Metastore service (for feature flags)
  NEXT_PUBLIC_METASTORE_URL: z
    .string()
    .url()
    .optional(),
});

/**
 * Parse and validate server environment variables.
 */
function parseServerEnv() {
  const parsed = serverEnvSchema.safeParse(process.env);

  if (!parsed.success) {
    console.error("❌ Invalid server environment variables:");
    console.error(parsed.error.flatten().fieldErrors);
    throw new Error("Invalid server environment configuration");
  }

  return parsed.data;
}

/**
 * Parse and validate client environment variables.
 */
function parseClientEnv() {
  const parsed = clientEnvSchema.safeParse({
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
    NEXT_PUBLIC_DEFAULT_TENANT_ID: process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID,
    NEXT_PUBLIC_FEATURE_FLAGS_ENABLED: process.env.NEXT_PUBLIC_FEATURE_FLAGS_ENABLED,
    NEXT_PUBLIC_LOG_LEVEL: process.env.NEXT_PUBLIC_LOG_LEVEL,
    NEXT_PUBLIC_METASTORE_URL: process.env.NEXT_PUBLIC_METASTORE_URL,
  });

  if (!parsed.success) {
    console.error("❌ Invalid client environment variables:");
    console.error(parsed.error.flatten().fieldErrors);
    throw new Error("Invalid client environment configuration");
  }

  return parsed.data;
}

/**
 * Server-side environment configuration.
 * Only use in server components, API routes, or server actions.
 */
export const serverEnv = parseServerEnv();

/**
 * Client-side environment configuration.
 * Safe to use in client components.
 */
export const clientEnv = parseClientEnv();

/**
 * Combined environment configuration.
 * Use serverEnv or clientEnv directly for better type safety.
 */
export const env = {
  ...serverEnv,
  ...clientEnv,
};

/**
 * Type definitions for environment variables.
 */
export type ServerEnv = z.infer<typeof serverEnvSchema>;
export type ClientEnv = z.infer<typeof clientEnvSchema>;
