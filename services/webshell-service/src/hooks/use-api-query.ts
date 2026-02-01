/**
 * React Query Hooks Factory
 *
 * Provides type-safe React Query hooks integrated with our API client.
 * Features:
 * - Automatic query key management
 * - Tenant-aware caching
 * - Optimistic updates
 * - Error handling integration
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
  type UseMutationOptions,
  type QueryKey,
} from "@tanstack/react-query";
import { apiClient, type ApiResponse, type RequestConfig } from "@/lib/api-client";
import { useCurrentTenant } from "@/contexts/tenant-context";

// ============================================================================
// Types
// ============================================================================

export interface QueryOptions<TData>
  extends Omit<UseQueryOptions<TData, Error>, "queryKey" | "queryFn"> {
  /** Additional request configuration */
  requestConfig?: RequestConfig;
}

export interface MutationOptions<TData, TVariables, TContext = unknown>
  extends Omit<UseMutationOptions<TData, Error, TVariables, TContext>, "mutationFn"> {
  /** Additional request configuration */
  requestConfig?: RequestConfig;
  /** Query keys to invalidate on success */
  invalidateKeys?: QueryKey[];
}

export type QueryKeyFactory = {
  all: readonly string[];
  lists: () => readonly [...readonly string[], string];
  list: (filters?: Record<string, unknown>) => readonly unknown[];
  details: () => readonly [...readonly string[], string];
  detail: (id: string | number) => readonly [...readonly string[], string, string | number];
};

// ============================================================================
// Query Key Factory
// ============================================================================

/**
 * Create a query key factory for a resource
 */
export function createQueryKeyFactory(resource: string): QueryKeyFactory {
  return {
    all: [resource] as const,
    lists: () => [...[resource], "list"] as const,
    list: (filters?: Record<string, unknown>) =>
      filters ? [...[resource], "list", filters] : [...[resource], "list"],
    details: () => [...[resource], "detail"] as const,
    detail: (id: string | number) => [...[resource], "detail", id] as const,
  };
}

// ============================================================================
// Query Hooks
// ============================================================================

/**
 * Hook for fetching a single resource
 */
export function useApiQuery<TData>(
  queryKey: QueryKey,
  path: string,
  options?: QueryOptions<TData>
) {
  const tenant = useCurrentTenant();
  const { requestConfig, ...queryOptions } = options ?? {};

  // Include tenant in query key for proper cache isolation
  const tenantQueryKey = tenant ? [...queryKey, { tenantId: tenant.id }] : queryKey;

  return useQuery<TData, Error>({
    queryKey: tenantQueryKey,
    queryFn: async () => {
      const response = await apiClient.get<TData>(path, {
        tenantId: tenant?.id,
        ...requestConfig,
      });
      return response.data;
    },
    ...queryOptions,
  });
}

/**
 * Hook for fetching a list of resources
 */
export function useApiListQuery<TData>(
  queryKey: QueryKey,
  path: string,
  params?: Record<string, string | number | boolean | undefined>,
  options?: QueryOptions<TData>
) {
  const tenant = useCurrentTenant();
  const { requestConfig, ...queryOptions } = options ?? {};

  // Include tenant and params in query key
  const fullQueryKey = [
    ...queryKey,
    ...(params ? [params] : []),
    ...(tenant ? [{ tenantId: tenant.id }] : []),
  ];

  return useQuery<TData, Error>({
    queryKey: fullQueryKey,
    queryFn: async () => {
      const response = await apiClient.get<TData>(path, {
        params,
        tenantId: tenant?.id,
        ...requestConfig,
      });
      return response.data;
    },
    ...queryOptions,
  });
}

// ============================================================================
// Mutation Hooks
// ============================================================================

/**
 * Hook for creating a resource
 * 
 * Automatically handles:
 * - Tenant context injection
 * - Cache invalidation on success (via invalidateKeys option)
 * 
 * @example
 * ```ts
 * const createUser = useApiCreateMutation<User, CreateUserInput>('/users', {
 *   invalidateKeys: [['users']],
 *   onSuccess: (data) => console.log('Created:', data),
 * });
 * 
 * createUser.mutate({ name: 'John', email: 'john@example.com' });
 * ```
 */
export function useApiCreateMutation<TData, TVariables, TContext = unknown>(
  path: string,
  options?: MutationOptions<TData, TVariables, TContext>
) {
  const queryClient = useQueryClient();
  const tenant = useCurrentTenant();
  const { requestConfig, invalidateKeys, ...mutationOptions } = options ?? {};

  return useMutation<TData, Error, TVariables, TContext>({
    mutationFn: async (data) => {
      const response = await apiClient.post<TData>(path, data, {
        tenantId: tenant?.id,
        ...requestConfig,
      });
      return response.data;
    },
    ...mutationOptions,
    // Wrap onSuccess to add invalidation
    onSuccess: async (...args) => {
      // Invalidate related queries on success
      if (invalidateKeys) {
        await Promise.all(
          invalidateKeys.map((key) => queryClient.invalidateQueries({ queryKey: key }))
        );
      }
      // Call user's onSuccess if provided (use type assertion for v5 compatibility)
      await (mutationOptions.onSuccess as ((...args: unknown[]) => unknown) | undefined)?.(...args);
    },
  });
}

/**
 * Hook for updating a resource
 * 
 * Automatically handles:
 * - Tenant context injection
 * - Cache invalidation on success
 * 
 * @example
 * ```ts
 * const updateUser = useApiUpdateMutation<User, UpdateUserInput>(
 *   (id) => `/users/${id}`,
 *   { invalidateKeys: [['users']] }
 * );
 * 
 * updateUser.mutate({ id: '123', name: 'Updated Name' });
 * ```
 */
export function useApiUpdateMutation<TData, TVariables extends { id: string | number }, TContext = unknown>(
  pathFn: (id: string | number) => string,
  options?: MutationOptions<TData, TVariables, TContext> & {
    /** Method to use (PUT or PATCH) */
    method?: "PUT" | "PATCH";
  }
) {
  const queryClient = useQueryClient();
  const tenant = useCurrentTenant();
  const { requestConfig, invalidateKeys, method = "PATCH", ...mutationOptions } = options ?? {};

  return useMutation<TData, Error, TVariables, TContext>({
    mutationFn: async (data) => {
      const path = pathFn(data.id);
      const apiMethod = method === "PUT" ? apiClient.put : apiClient.patch;
      const response = await apiMethod.call(apiClient, path, data, {
        tenantId: tenant?.id,
        ...requestConfig,
      }) as ApiResponse<TData>;
      return response.data;
    },
    ...mutationOptions,
    onSuccess: async (...args) => {
      if (invalidateKeys) {
        await Promise.all(
          invalidateKeys.map((key) => queryClient.invalidateQueries({ queryKey: key }))
        );
      }
      await (mutationOptions.onSuccess as ((...args: unknown[]) => unknown) | undefined)?.(...args);
    },
  });
}

/**
 * Hook for deleting a resource
 * 
 * Automatically handles:
 * - Tenant context injection
 * - Cache invalidation on success
 * 
 * @example
 * ```ts
 * const deleteUser = useApiDeleteMutation(
 *   (id) => `/users/${id}`,
 *   { invalidateKeys: [['users']] }
 * );
 * 
 * deleteUser.mutate('123');
 * ```
 */
export function useApiDeleteMutation<TData = void, TContext = unknown>(
  pathFn: (id: string | number) => string,
  options?: MutationOptions<TData, string | number, TContext>
) {
  const queryClient = useQueryClient();
  const tenant = useCurrentTenant();
  const { requestConfig, invalidateKeys, ...mutationOptions } = options ?? {};

  return useMutation<TData, Error, string | number, TContext>({
    mutationFn: async (id) => {
      const path = pathFn(id);
      const response = await apiClient.delete<TData>(path, {
        tenantId: tenant?.id,
        ...requestConfig,
      });
      return response.data;
    },
    ...mutationOptions,
    onSuccess: async (...args) => {
      if (invalidateKeys) {
        await Promise.all(
          invalidateKeys.map((key) => queryClient.invalidateQueries({ queryKey: key }))
        );
      }
      await (mutationOptions.onSuccess as ((...args: unknown[]) => unknown) | undefined)?.(...args);
    },
  });
}

// ============================================================================
// Prefetch Utilities
// ============================================================================

/**
 * Prefetch a query (useful for hover prefetching)
 */
export function usePrefetch() {
  const queryClient = useQueryClient();
  const tenant = useCurrentTenant();

  return {
    prefetchQuery: <TData>(queryKey: QueryKey, path: string, config?: RequestConfig) => {
      const tenantQueryKey = tenant ? [...queryKey, { tenantId: tenant.id }] : queryKey;
      
      return queryClient.prefetchQuery({
        queryKey: tenantQueryKey,
        queryFn: async () => {
          const response = await apiClient.get<TData>(path, {
            tenantId: tenant?.id,
            ...config,
          });
          return response.data;
        },
      });
    },
  };
}

// ============================================================================
// Cache Utilities
// ============================================================================

/**
 * Hook for cache manipulation
 */
export function useQueryCache() {
  const queryClient = useQueryClient();

  return {
    /**
     * Invalidate queries by key
     */
    invalidate: (queryKey: QueryKey) => {
      return queryClient.invalidateQueries({ queryKey });
    },

    /**
     * Set query data directly
     */
    setData: <TData>(queryKey: QueryKey, data: TData) => {
      return queryClient.setQueryData(queryKey, data);
    },

    /**
     * Get query data
     */
    getData: <TData>(queryKey: QueryKey): TData | undefined => {
      return queryClient.getQueryData(queryKey);
    },

    /**
     * Remove query from cache
     */
    remove: (queryKey: QueryKey) => {
      return queryClient.removeQueries({ queryKey });
    },

    /**
     * Clear all queries
     */
    clear: () => {
      return queryClient.clear();
    },
  };
}
