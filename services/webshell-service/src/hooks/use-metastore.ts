/**
 * Metastore Hooks
 *
 * React Query hooks for feature flags and metadata management.
 * Provides caching, mutations, and optimistic updates.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  keepPreviousData,
} from "@tanstack/react-query";
import {
  fetchFeatureFlags,
  fetchFeatureFlag,
  createFeatureFlag,
  updateFeatureFlag,
  deleteFeatureFlag,
  toggleFeatureFlag,
  addTargetingRule,
  removeTargetingRule,
  fetchMetadata,
  fetchMetadataEntry,
  createMetadata,
  updateMetadata,
  deleteMetadata,
  metastoreQueryKeys,
} from "@/services/metastore-api";
import type {
  FeatureFlag,
  FeatureFlagQueryParams,
  CreateFeatureFlagRequest,
  UpdateFeatureFlagRequest,
  AddTargetingRuleRequest,
  MetadataEntry,
  MetadataQueryParams,
  CreateMetadataRequest,
  UpdateMetadataRequest,
} from "@/types/metastore";

// ============================================================================
// Query Options
// ============================================================================

const DEFAULT_STALE_TIME = 30 * 1000; // 30 seconds
const DEFAULT_GC_TIME = 5 * 60 * 1000; // 5 minutes

// ============================================================================
// Feature Flag Hooks
// ============================================================================

/**
 * Hook for fetching paginated feature flags
 */
export function useFeatureFlags(params: FeatureFlagQueryParams = {}) {
  return useQuery({
    queryKey: metastoreQueryKeys.featureFlags.list(params),
    queryFn: async () => {
      const response = await fetchFeatureFlags(params);
      return response.data;
    },
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_GC_TIME,
    placeholderData: keepPreviousData,
  });
}

/**
 * Hook for fetching a single feature flag
 */
export function useFeatureFlag(idOrName: string | null) {
  return useQuery({
    queryKey: metastoreQueryKeys.featureFlags.detail(idOrName ?? ""),
    queryFn: async () => {
      if (!idOrName) throw new Error("Feature flag ID or name is required");
      const response = await fetchFeatureFlag(idOrName);
      return response.data;
    },
    enabled: !!idOrName,
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_GC_TIME,
  });
}

/**
 * Hook for creating a feature flag
 */
export function useCreateFeatureFlag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateFeatureFlagRequest) => createFeatureFlag(data),
    onSuccess: () => {
      // Invalidate feature flags list to refetch
      queryClient.invalidateQueries({
        queryKey: metastoreQueryKeys.featureFlags.lists(),
      });
    },
  });
}

/**
 * Hook for updating a feature flag
 */
export function useUpdateFeatureFlag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateFeatureFlagRequest }) =>
      updateFeatureFlag(id, data),
    onSuccess: (_, variables) => {
      // Invalidate both list and detail queries
      queryClient.invalidateQueries({
        queryKey: metastoreQueryKeys.featureFlags.lists(),
      });
      queryClient.invalidateQueries({
        queryKey: metastoreQueryKeys.featureFlags.detail(variables.id),
      });
    },
  });
}

/**
 * Hook for deleting a feature flag
 */
export function useDeleteFeatureFlag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (id: string) => deleteFeatureFlag(id),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: metastoreQueryKeys.featureFlags.lists(),
      });
    },
  });
}

/**
 * Hook for toggling a feature flag
 */
export function useToggleFeatureFlag() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ id, enabled }: { id: string; enabled: boolean }) =>
      toggleFeatureFlag(id, enabled),
    // Optimistic update
    onMutate: async ({ id, enabled }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({
        queryKey: metastoreQueryKeys.featureFlags.detail(id),
      });

      // Snapshot previous value
      const previousFlag = queryClient.getQueryData<FeatureFlag>(
        metastoreQueryKeys.featureFlags.detail(id)
      );

      // Optimistically update the flag
      if (previousFlag) {
        queryClient.setQueryData(
          metastoreQueryKeys.featureFlags.detail(id),
          { ...previousFlag, enabled }
        );
      }

      return { previousFlag };
    },
    onError: (_, variables, context) => {
      // Rollback on error
      if (context?.previousFlag) {
        queryClient.setQueryData(
          metastoreQueryKeys.featureFlags.detail(variables.id),
          context.previousFlag
        );
      }
    },
    onSettled: (_, __, variables) => {
      // Always refetch after error or success
      queryClient.invalidateQueries({
        queryKey: metastoreQueryKeys.featureFlags.detail(variables.id),
      });
      queryClient.invalidateQueries({
        queryKey: metastoreQueryKeys.featureFlags.lists(),
      });
    },
  });
}

/**
 * Hook for adding a targeting rule
 */
export function useAddTargetingRule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      flagId,
      rule,
    }: {
      flagId: string;
      rule: AddTargetingRuleRequest;
    }) => addTargetingRule(flagId, rule),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: metastoreQueryKeys.featureFlags.detail(variables.flagId),
      });
    },
  });
}

/**
 * Hook for removing a targeting rule
 */
export function useRemoveTargetingRule() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ flagId, ruleId }: { flagId: string; ruleId: string }) =>
      removeTargetingRule(flagId, ruleId),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: metastoreQueryKeys.featureFlags.detail(variables.flagId),
      });
    },
  });
}

// ============================================================================
// Metadata Hooks
// ============================================================================

/**
 * Hook for fetching metadata entries
 */
export function useMetadata(params: MetadataQueryParams = {}) {
  return useQuery({
    queryKey: metastoreQueryKeys.metadata.list(params),
    queryFn: async () => {
      const response = await fetchMetadata(params);
      return response.data;
    },
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_GC_TIME,
    placeholderData: keepPreviousData,
  });
}

/**
 * Hook for fetching a single metadata entry
 */
export function useMetadataEntry(key: string | null) {
  return useQuery({
    queryKey: metastoreQueryKeys.metadata.detail(key ?? ""),
    queryFn: async () => {
      if (!key) throw new Error("Metadata key is required");
      const response = await fetchMetadataEntry(key);
      return response.data;
    },
    enabled: !!key,
    staleTime: DEFAULT_STALE_TIME,
    gcTime: DEFAULT_GC_TIME,
  });
}

/**
 * Hook for creating metadata
 */
export function useCreateMetadata() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateMetadataRequest) => createMetadata(data),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: metastoreQueryKeys.metadata.lists(),
      });
    },
  });
}

/**
 * Hook for updating metadata
 */
export function useUpdateMetadata() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ key, data }: { key: string; data: UpdateMetadataRequest }) =>
      updateMetadata(key, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({
        queryKey: metastoreQueryKeys.metadata.lists(),
      });
      queryClient.invalidateQueries({
        queryKey: metastoreQueryKeys.metadata.detail(variables.key),
      });
    },
  });
}

/**
 * Hook for deleting metadata
 */
export function useDeleteMetadata() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (key: string) => deleteMetadata(key),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: metastoreQueryKeys.metadata.lists(),
      });
    },
  });
}

// ============================================================================
// Utility Hooks
// ============================================================================

/**
 * Hook for getting unique tags from feature flags
 */
export function useFeatureFlagTags() {
  const { data } = useFeatureFlags({ page_size: 100 });

  const tags = new Set<string>();
  if (data?.items) {
    data.items.forEach((flag: FeatureFlag) => {
      flag.tags.forEach((tag) => tags.add(tag));
    });
  }

  return Array.from(tags).sort();
}

/**
 * Hook for checking if a feature is enabled for the current context
 */
export function useFeatureEnabled(flagName: string, defaultValue = false) {
  const { data, isLoading, error } = useFeatureFlag(flagName);

  if (isLoading || error || !data) {
    return { enabled: defaultValue, isLoading, error };
  }

  return { enabled: data.enabled, isLoading: false, error: null };
}
