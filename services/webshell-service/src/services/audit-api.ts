/**
 * Audit API Client
 *
 * Service layer for interacting with the audit-service API.
 * Provides typed methods for fetching and managing audit logs.
 */

import { apiClient, type ApiResponse } from "@/lib/api-client";
import type {
  AuditEvent,
  AuditQueryParams,
  PaginatedAuditEvents,
} from "@/types/audit";

// ============================================================================
// API Endpoints
// ============================================================================

const AUDIT_API_BASE = "/api/v1/audit";

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch paginated audit events with optional filters
 */
export async function fetchAuditEvents(
  params: AuditQueryParams = {}
): Promise<ApiResponse<PaginatedAuditEvents>> {
  const queryParams: Record<string, string | number | boolean | undefined> = {
    page: params.page ?? 1,
    page_size: params.page_size ?? 20,
  };

  // Add optional filters
  if (params.actor_id) queryParams.actor_id = params.actor_id;
  if (params.resource_type) queryParams.resource_type = params.resource_type;
  if (params.action) queryParams.action = params.action;
  if (params.severity) queryParams.severity = params.severity;
  if (params.start_date) queryParams.start_date = params.start_date;
  if (params.end_date) queryParams.end_date = params.end_date;
  if (params.search_text) queryParams.search_text = params.search_text;

  return apiClient.get<PaginatedAuditEvents>(`${AUDIT_API_BASE}/events`, {
    params: queryParams,
  });
}

/**
 * Fetch a single audit event by ID
 */
export async function fetchAuditEvent(
  eventId: string
): Promise<ApiResponse<AuditEvent>> {
  return apiClient.get<AuditEvent>(`${AUDIT_API_BASE}/events/${eventId}`);
}

/**
 * Export audit events as CSV or JSON
 */
export async function exportAuditEvents(
  params: AuditQueryParams & { format?: "csv" | "json" }
): Promise<ApiResponse<Blob>> {
  const format = params.format ?? "csv";
  const queryParams: Record<string, string | number | boolean | undefined> = {
    format,
  };

  if (params.actor_id) queryParams.actor_id = params.actor_id;
  if (params.resource_type) queryParams.resource_type = params.resource_type;
  if (params.action) queryParams.action = params.action;
  if (params.severity) queryParams.severity = params.severity;
  if (params.start_date) queryParams.start_date = params.start_date;
  if (params.end_date) queryParams.end_date = params.end_date;

  return apiClient.get<Blob>(`${AUDIT_API_BASE}/events/export`, {
    params: queryParams,
    headers: {
      Accept: format === "csv" ? "text/csv" : "application/json",
    },
  });
}

// ============================================================================
// Query Key Factory
// ============================================================================

/**
 * Query keys for React Query caching
 */
export const auditQueryKeys = {
  all: ["audit"] as const,
  lists: () => [...auditQueryKeys.all, "list"] as const,
  list: (params: AuditQueryParams) => [...auditQueryKeys.lists(), params] as const,
  details: () => [...auditQueryKeys.all, "detail"] as const,
  detail: (id: string) => [...auditQueryKeys.details(), id] as const,
};
