/**
 * Feature Flags Dashboard Page
 *
 * Manage feature flags: create, edit, toggle, delete.
 */
"use client";

import { useState, useCallback } from "react";
import { Flag } from "lucide-react";
import { FeatureFlagTable, FeatureFlagForm } from "@/components/metastore";
import {
  useFeatureFlags,
  useCreateFeatureFlag,
  useUpdateFeatureFlag,
  useDeleteFeatureFlag,
  useToggleFeatureFlag,
} from "@/hooks/use-metastore";
import { useDebounce } from "@/hooks/use-debounce";
import type { FeatureFlag, CreateFeatureFlagRequest, UpdateFeatureFlagRequest } from "@/types/metastore";

const PAGE_SIZE = 20;

export default function FeatureFlagsPage() {
  // Pagination and search state
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounce(search, 300);

  // Form state
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingFlag, setEditingFlag] = useState<FeatureFlag | undefined>();

  // Queries
  const { data, isLoading, refetch } = useFeatureFlags({
    page,
    page_size: PAGE_SIZE,
    search: debouncedSearch || undefined,
  });

  // Mutations
  const createMutation = useCreateFeatureFlag();
  const updateMutation = useUpdateFeatureFlag();
  const deleteMutation = useDeleteFeatureFlag();
  const toggleMutation = useToggleFeatureFlag();

  // Handlers
  const handleCreate = useCallback(() => {
    setEditingFlag(undefined);
    setIsFormOpen(true);
  }, []);

  const handleEdit = useCallback((flag: FeatureFlag) => {
    setEditingFlag(flag);
    setIsFormOpen(true);
  }, []);

  const handleDelete = useCallback(async (flag: FeatureFlag) => {
    if (window.confirm(`Are you sure you want to delete "${flag.name}"?`)) {
      try {
        await deleteMutation.mutateAsync(flag.id);
      } catch (error) {
        console.error("Failed to delete feature flag:", error);
      }
    }
  }, [deleteMutation]);

  const handleToggle = useCallback(async (flag: FeatureFlag) => {
    try {
      await toggleMutation.mutateAsync({
        id: flag.id,
        enabled: !flag.enabled,
      });
    } catch (error) {
      console.error("Failed to toggle feature flag:", error);
    }
  }, [toggleMutation]);

  const handleFormSubmit = useCallback(async (data: CreateFeatureFlagRequest | UpdateFeatureFlagRequest) => {
    try {
      if (editingFlag) {
        await updateMutation.mutateAsync({
          id: editingFlag.id,
          data: data as UpdateFeatureFlagRequest,
        });
      } else {
        await createMutation.mutateAsync(data as CreateFeatureFlagRequest);
      }
      setIsFormOpen(false);
      setEditingFlag(undefined);
    } catch (error) {
      console.error("Failed to save feature flag:", error);
    }
  }, [editingFlag, createMutation, updateMutation]);

  const handleFormClose = useCallback(() => {
    setIsFormOpen(false);
    setEditingFlag(undefined);
  }, []);

  const handleRefresh = useCallback(() => {
    refetch();
  }, [refetch]);

  const handleSearchChange = useCallback((value: string) => {
    setSearch(value);
    setPage(1); // Reset to first page on search
  }, []);

  const handlePageChange = useCallback((newPage: number) => {
    setPage(newPage);
  }, []);

  return (
    <div className="p-6">
      {/* Page Header */}
      <div className="mb-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-100">
            <Flag className="h-5 w-5 text-purple-600" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Feature Flags</h1>
            <p className="text-sm text-gray-500">
              Manage feature toggles with targeting rules and rollout controls
            </p>
          </div>
        </div>
      </div>

      {/* Table */}
      <FeatureFlagTable
        data={data}
        isLoading={isLoading}
        page={page}
        pageSize={PAGE_SIZE}
        onPageChange={handlePageChange}
        onToggle={handleToggle}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onCreate={handleCreate}
        onRefresh={handleRefresh}
        searchValue={search}
        onSearchChange={handleSearchChange}
      />

      {/* Form Modal */}
      <FeatureFlagForm
        flag={editingFlag}
        isOpen={isFormOpen}
        onClose={handleFormClose}
        onSubmit={handleFormSubmit}
        isSubmitting={createMutation.isPending || updateMutation.isPending}
      />
    </div>
  );
}
