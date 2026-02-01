/**
 * Metastore API Client
 *
 * Service layer for interacting with the metastore-service API.
 * Provides typed methods for feature flags, metadata, and configuration.
 */

import { apiClient, type ApiResponse } from "@/lib/api-client";
import type {
  FeatureFlag,
  FeatureFlagQueryParams,
  PaginatedFeatureFlags,
  CreateFeatureFlagRequest,
  UpdateFeatureFlagRequest,
  AddTargetingRuleRequest,
  TargetingRule,
  EvaluateFeatureFlagRequest,
  EvaluateFeatureFlagResponse,
  MetadataEntry,
  MetadataQueryParams,
  PaginatedMetadata,
  CreateMetadataRequest,
  UpdateMetadataRequest,
} from "@/types/metastore";

// ============================================================================
// API Endpoints
// ============================================================================

const METASTORE_API_BASE = "/api/v1/metastore";

// ============================================================================
// Feature Flag API Functions
// ============================================================================

/**
 * Fetch paginated feature flags with optional filters
 */
export async function fetchFeatureFlags(
  params: FeatureFlagQueryParams = {}
): Promise<ApiResponse<PaginatedFeatureFlags>> {
  const queryParams: Record<string, string | number | boolean | undefined> = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20,
  };

  if (params.enabled !== undefined) queryParams.enabled = params.enabled;
  if (params.search) queryParams.search = params.search;
  if (params.environment) queryParams.environment = params.environment;
  if (params.tags?.length) queryParams.tags = params.tags.join(",");

  return apiClient.get<PaginatedFeatureFlags>(`${METASTORE_API_BASE}/feature-flags`, {
    params: queryParams,
  });
}

/**
 * Fetch a single feature flag by ID or name
 */
export async function fetchFeatureFlag(
  idOrName: string
): Promise<ApiResponse<FeatureFlag>> {
  return apiClient.get<FeatureFlag>(`${METASTORE_API_BASE}/feature-flags/${idOrName}`);
}

/**
 * Create a new feature flag
 */
export async function createFeatureFlag(
  data: CreateFeatureFlagRequest
): Promise<ApiResponse<FeatureFlag>> {
  return apiClient.post<FeatureFlag>(`${METASTORE_API_BASE}/feature-flags`, {
    body: JSON.stringify(data),
  });
}

/**
 * Update an existing feature flag
 */
export async function updateFeatureFlag(
  id: string,
  data: UpdateFeatureFlagRequest
): Promise<ApiResponse<FeatureFlag>> {
  return apiClient.patch<FeatureFlag>(`${METASTORE_API_BASE}/feature-flags/${id}`, {
    body: JSON.stringify(data),
  });
}

/**
 * Delete a feature flag
 */
export async function deleteFeatureFlag(id: string): Promise<ApiResponse<void>> {
  return apiClient.delete<void>(`${METASTORE_API_BASE}/feature-flags/${id}`);
}

/**
 * Toggle feature flag enabled state
 */
export async function toggleFeatureFlag(
  id: string,
  enabled: boolean
): Promise<ApiResponse<FeatureFlag>> {
  return apiClient.patch<FeatureFlag>(`${METASTORE_API_BASE}/feature-flags/${id}`, {
    body: JSON.stringify({ enabled }),
  });
}

/**
 * Add a targeting rule to a feature flag
 */
export async function addTargetingRule(
  flagId: string,
  rule: AddTargetingRuleRequest
): Promise<ApiResponse<TargetingRule>> {
  return apiClient.post<TargetingRule>(
    `${METASTORE_API_BASE}/feature-flags/${flagId}/rules`,
    { body: JSON.stringify(rule) }
  );
}

/**
 * Remove a targeting rule from a feature flag
 */
export async function removeTargetingRule(
  flagId: string,
  ruleId: string
): Promise<ApiResponse<void>> {
  return apiClient.delete<void>(
    `${METASTORE_API_BASE}/feature-flags/${flagId}/rules/${ruleId}`
  );
}

/**
 * Evaluate a feature flag
 */
export async function evaluateFeatureFlag(
  flagName: string,
  request: EvaluateFeatureFlagRequest
): Promise<ApiResponse<EvaluateFeatureFlagResponse>> {
  return apiClient.post<EvaluateFeatureFlagResponse>(
    `${METASTORE_API_BASE}/feature-flags/${flagName}/evaluate`,
    { body: JSON.stringify(request) }
  );
}

// ============================================================================
// Metadata API Functions
// ============================================================================

/**
 * Fetch all metadata entries
 */
export async function fetchMetadata(
  params: MetadataQueryParams = {}
): Promise<ApiResponse<MetadataEntry[]>> {
  const queryParams: Record<string, string | number | boolean | undefined> = {};

  if (params.prefix) queryParams.prefix = params.prefix;
  if (params.search) queryParams.search = params.search;

  return apiClient.get<MetadataEntry[]>(`${METASTORE_API_BASE}/metadata`, {
    params: queryParams,
  });
}

/**
 * Fetch a single metadata entry by key
 */
export async function fetchMetadataEntry(
  key: string
): Promise<ApiResponse<MetadataEntry>> {
  return apiClient.get<MetadataEntry>(`${METASTORE_API_BASE}/metadata/${key}`);
}

/**
 * Create a new metadata entry
 */
export async function createMetadata(
  data: CreateMetadataRequest
): Promise<ApiResponse<MetadataEntry>> {
  return apiClient.post<MetadataEntry>(`${METASTORE_API_BASE}/metadata`, {
    body: JSON.stringify(data),
  });
}

/**
 * Update a metadata entry
 */
export async function updateMetadata(
  key: string,
  data: UpdateMetadataRequest
): Promise<ApiResponse<MetadataEntry>> {
  return apiClient.put<MetadataEntry>(`${METASTORE_API_BASE}/metadata/${key}`, {
    body: JSON.stringify(data),
  });
}

/**
 * Delete a metadata entry
 */
export async function deleteMetadata(key: string): Promise<ApiResponse<void>> {
  return apiClient.delete<void>(`${METASTORE_API_BASE}/metadata/${key}`);
}

// ============================================================================
// Query Key Factory
// ============================================================================

/**
 * Query keys for React Query caching
 */
export const metastoreQueryKeys = {
  // Feature flags
  featureFlags: {
    all: ["feature-flags"] as const,
    lists: () => [...metastoreQueryKeys.featureFlags.all, "list"] as const,
    list: (params: FeatureFlagQueryParams) =>
      [...metastoreQueryKeys.featureFlags.lists(), params] as const,
    details: () => [...metastoreQueryKeys.featureFlags.all, "detail"] as const,
    detail: (id: string) =>
      [...metastoreQueryKeys.featureFlags.details(), id] as const,
  },
  // Metadata
  metadata: {
    all: ["metadata"] as const,
    lists: () => [...metastoreQueryKeys.metadata.all, "list"] as const,
    list: (params: MetadataQueryParams) =>
      [...metastoreQueryKeys.metadata.lists(), params] as const,
    details: () => [...metastoreQueryKeys.metadata.all, "detail"] as const,
    detail: (key: string) =>
      [...metastoreQueryKeys.metadata.details(), key] as const,
  },
};
