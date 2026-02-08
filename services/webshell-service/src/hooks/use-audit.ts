/**
 * Audit Hooks
 *
 * React Query hooks for fetching and managing audit data.
 * Provides caching, background refetching, and error handling.
 */

import { useQuery, useInfiniteQuery, keepPreviousData } from "@tanstack/react-query";
import {
  fetchAuditEvents,
  fetchAuditEvent,
  auditQueryKeys,
} from "@/services/audit-api";
import type { AuditQueryParams, AuditEvent, PaginatedAuditEvents } from "@/types/audit";

// ============================================================================
// Query Options
// ============================================================================

const DEFAULT_STALE_TIME = 30 * 1000; // 30 seconds
const DEFAULT_GC_TIME = 5 * 60 * 1000; // 5 minutes

// ============================================================================
// Hooks
// ============================================================================

/**
 * Hook for fetching paginated audit events
 */
export function useAuditEvents(params: AuditQueryParams = {}) {
  return useQuery({
    queryKey: auditQueryKeys.list(params),
    queryFn: async () => {
      const response = await fetchAuditEvents(params);
      return response.data;
    },
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_GC_TIME,
    placeholderData: keepPreviousData,
  });
}

/**
 * Hook for infinite scrolling of audit events
 */
export function useInfiniteAuditEvents(
  params: Omit<AuditQueryParams, "page"> = {}
) {
  return useInfiniteQuery({
    queryKey: [...auditQueryKeys.lists(), "infinite", params],
    queryFn: async ({ pageParam = 1 }) => {
      const response = await fetchAuditEvents({
        ...params,
        page: pageParam,
      });
      return response.data;
    },
    initialPageParam: 1,
    getNextPageParam: (lastPage: PaginatedAuditEvents) => {
      if (lastPage.has_next) {
        return lastPage.page + 1;
      }
      return undefined;
    },
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_GC_TIME,
  });
}

/**
 * Hook for fetching a single audit event
 */
export function useAuditEvent(eventId: string | null) {
  return useQuery({
    queryKey: auditQueryKeys.detail(eventId ?? ""),
    queryFn: async () => {
      if (!eventId) throw new Error("Event ID is required");
      const response = await fetchAuditEvent(eventId);
      return response.data;
    },
    enabled: !!eventId,
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_GC_TIME,
  });
}

/**
 * Hook for getting distinct filter values from audit data
 * This provides autocomplete suggestions for filters
 */
export function useAuditFilterOptions() {
  const { data } = useAuditEvents({ page_size: 100 });

  const options = {
    resourceTypes: [] as string[],
    actorIds: [] as string[],
    serviceNames: [] as string[],
  };

  if (data?.items) {
    const resourceTypesSet = new Set<string>();
    const actorIdsSet = new Set<string>();
    const serviceNamesSet = new Set<string>();

    data.items.forEach((event: AuditEvent) => {
      resourceTypesSet.add(event.resource_type);
      actorIdsSet.add(event.actor_id);
      serviceNamesSet.add(event.service_name);
    });

    options.resourceTypes = Array.from(resourceTypesSet).sort();
    options.actorIds = Array.from(actorIdsSet).sort();
    options.serviceNames = Array.from(serviceNamesSet).sort();
  }

  return options;
}
