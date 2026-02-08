/**
 * API Client - Type-safe HTTP client with enterprise features
 *
 * Features:
 * - Automatic tenant header injection
 * - Authentication token handling
 * - Request/response interceptors
 * - Error normalization
 * - Retry logic with exponential backoff
 * - Request timeout handling
 * - Request cancellation support
 */

import { getSession } from "next-auth/react";
import { clientEnv } from "@/config/env";

// ============================================================================
// Types
// ============================================================================

export interface ApiClientConfig {
  baseUrl: string;
  timeout?: number;
  retries?: number;
  retryDelay?: number;
}

export interface RequestConfig extends RequestInit {
  /** Custom timeout for this request (ms) */
  timeout?: number;
  /** Skip authentication header */
  skipAuth?: boolean;
  /** Skip tenant header */
  skipTenant?: boolean;
  /** Custom tenant ID override */
  tenantId?: string;
  /** Number of retries for this request */
  retries?: number;
  /** Query parameters */
  params?: Record<string, string | number | boolean | undefined>;
}

export interface ApiResponse<T = unknown> {
  data: T;
  status: number;
  headers: Headers;
  ok: boolean;
}

export interface ApiError extends Error {
  status: number;
  statusText: string;
  data: unknown;
  isNetworkError: boolean;
  isTimeoutError: boolean;
  isAbortError: boolean;
}

// ============================================================================
// Error Handling
// ============================================================================

/**
 * Create a normalized API error
 */
function createApiError(
  message: string,
  status: number,
  statusText: string,
  data: unknown = null,
  options: { isNetworkError?: boolean; isTimeoutError?: boolean; isAbortError?: boolean } = {}
): ApiError {
  const error = new Error(message) as ApiError;
  error.name = "ApiError";
  error.status = status;
  error.statusText = statusText;
  error.data = data;
  error.isNetworkError = options.isNetworkError ?? false;
  error.isTimeoutError = options.isTimeoutError ?? false;
  error.isAbortError = options.isAbortError ?? false;
  return error;
}

/**
 * Type guard for ApiError
 */
export function isApiError(error: unknown): error is ApiError {
  return error instanceof Error && error.name === "ApiError";
}

// ============================================================================
// Utility Functions
// ============================================================================

/**
 * Build URL with query parameters
 */
function buildUrl(
  baseUrl: string,
  path: string,
  params?: Record<string, string | number | boolean | undefined>
): string {
  // Ensure path starts with /
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const url = new URL(normalizedPath, baseUrl);

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) {
        url.searchParams.append(key, String(value));
      }
    });
  }

  return url.toString();
}

/**
 * Sleep for a given number of milliseconds
 */
function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Get current tenant ID from storage
 */
function getCurrentTenantId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem("webshell_current_tenant_id");
  } catch {
    return null;
  }
}

// ============================================================================
// API Client Class
// ============================================================================

export class ApiClient {
  private baseUrl: string;
  private defaultTimeout: number;
  private defaultRetries: number;
  private retryDelay: number;

  constructor(config: ApiClientConfig) {
    this.baseUrl = config.baseUrl;
    this.defaultTimeout = config.timeout ?? 30000; // 30 seconds
    this.defaultRetries = config.retries ?? 3;
    this.retryDelay = config.retryDelay ?? 1000; // 1 second
  }

  /**
   * Make an HTTP request
   */
  async request<T>(path: string, config: RequestConfig = {}): Promise<ApiResponse<T>> {
    const {
      timeout = this.defaultTimeout,
      skipAuth = false,
      skipTenant = false,
      tenantId,
      retries = this.defaultRetries,
      params,
      headers: customHeaders,
      ...fetchConfig
    } = config;

    const url = buildUrl(this.baseUrl, path, params);

    // Build headers
    const headers = new Headers(customHeaders);

    // Set default content type for JSON
    if (!headers.has("Content-Type") && fetchConfig.body) {
      headers.set("Content-Type", "application/json");
    }

    // Add authentication header
    if (!skipAuth) {
      const session = await getSession();
      if (session?.accessToken) {
        headers.set("Authorization", `Bearer ${session.accessToken}`);
      }
    }

    // Add tenant header
    if (!skipTenant) {
      const effectiveTenantId = tenantId ?? getCurrentTenantId();
      if (effectiveTenantId) {
        headers.set("X-Tenant-ID", effectiveTenantId);
      }
    }

    // Create abort controller for timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeout);

    // Merge signal if provided
    if (config.signal) {
      config.signal.addEventListener("abort", () => controller.abort());
    }

    let lastError: ApiError | null = null;
    let attempt = 0;

    while (attempt <= retries) {
      try {
        const response = await fetch(url, {
          ...fetchConfig,
          headers,
          signal: controller.signal,
        });

        clearTimeout(timeoutId);

        // Parse response
        let data: T;
        const contentType = response.headers.get("Content-Type");

        if (contentType?.includes("application/json")) {
          data = await response.json();
        } else if (contentType?.includes("text/")) {
          data = (await response.text()) as T;
        } else {
          data = (await response.blob()) as T;
        }

        // Handle error responses
        if (!response.ok) {
          throw createApiError(
            `Request failed with status ${response.status}`,
            response.status,
            response.statusText,
            data
          );
        }

        return {
          data,
          status: response.status,
          headers: response.headers,
          ok: response.ok,
        };
      } catch (error) {
        clearTimeout(timeoutId);

        // Handle abort errors
        if (error instanceof Error && error.name === "AbortError") {
          // Check if it was a timeout or user cancellation
          if (config.signal?.aborted) {
            throw createApiError("Request was cancelled", 0, "Aborted", null, {
              isAbortError: true,
            });
          }
          throw createApiError("Request timed out", 0, "Timeout", null, {
            isTimeoutError: true,
          });
        }

        // Handle network errors
        if (error instanceof TypeError && error.message === "Failed to fetch") {
          lastError = createApiError("Network error", 0, "Network Error", null, {
            isNetworkError: true,
          });
        } else if (isApiError(error)) {
          lastError = error;
        } else {
          lastError = createApiError(
            error instanceof Error ? error.message : "Unknown error",
            0,
            "Unknown",
            null
          );
        }

        // Don't retry on client errors (4xx) except for specific cases
        if (lastError.status >= 400 && lastError.status < 500) {
          // Retry on rate limiting
          if (lastError.status !== 429) {
            throw lastError;
          }
        }

        // Check if we should retry
        if (attempt < retries) {
          // Exponential backoff with jitter
          const delay = this.retryDelay * Math.pow(2, attempt) + Math.random() * 1000;
          await sleep(delay);
          attempt++;
        } else {
          throw lastError;
        }
      }
    }

    // Should never reach here, but TypeScript needs this
    throw lastError ?? createApiError("Unknown error", 0, "Unknown", null);
  }

  /**
   * HTTP GET request
   */
  async get<T>(path: string, config?: RequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>(path, { ...config, method: "GET" });
  }

  /**
   * HTTP POST request
   */
  async post<T>(
    path: string,
    data?: unknown,
    config?: RequestConfig
  ): Promise<ApiResponse<T>> {
    return this.request<T>(path, {
      ...config,
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * HTTP PUT request
   */
  async put<T>(
    path: string,
    data?: unknown,
    config?: RequestConfig
  ): Promise<ApiResponse<T>> {
    return this.request<T>(path, {
      ...config,
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * HTTP PATCH request
   */
  async patch<T>(
    path: string,
    data?: unknown,
    config?: RequestConfig
  ): Promise<ApiResponse<T>> {
    return this.request<T>(path, {
      ...config,
      method: "PATCH",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * HTTP DELETE request
   */
  async delete<T>(path: string, config?: RequestConfig): Promise<ApiResponse<T>> {
    return this.request<T>(path, { ...config, method: "DELETE" });
  }
}

// ============================================================================
// Default Client Instance
// ============================================================================

/**
 * Default API client instance configured for the main API gateway
 */
export const apiClient = new ApiClient({
  baseUrl: clientEnv.NEXT_PUBLIC_API_URL,
  timeout: 30000,
  retries: 3,
  retryDelay: 1000,
});

/**
 * Create a custom API client with specific configuration
 */
export function createApiClient(config: ApiClientConfig): ApiClient {
  return new ApiClient(config);
}
