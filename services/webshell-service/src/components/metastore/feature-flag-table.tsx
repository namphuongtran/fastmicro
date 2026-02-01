/**
 * Feature Flag Table Component
 *
 * Displays feature flags in a sortable, filterable table with actions.
 */
"use client";

import { useState } from "react";
import { format } from "date-fns";
import {
  Flag,
  ToggleLeft,
  ToggleRight,
  Pencil,
  Trash2,
  ChevronLeft,
  ChevronRight,
  RefreshCw,
  Plus,
  Search,
  Filter,
} from "lucide-react";
import type { FeatureFlag, PaginatedFeatureFlags } from "@/types/metastore";

interface FeatureFlagTableProps {
  /** Feature flags data */
  data: PaginatedFeatureFlags | undefined;
  /** Whether data is loading */
  isLoading: boolean;
  /** Current page number */
  page: number;
  /** Page size */
  pageSize: number;
  /** Callback when page changes */
  onPageChange: (page: number) => void;
  /** Callback when toggle is clicked */
  onToggle: (flag: FeatureFlag) => void;
  /** Callback when edit is clicked */
  onEdit: (flag: FeatureFlag) => void;
  /** Callback when delete is clicked */
  onDelete: (flag: FeatureFlag) => void;
  /** Callback when create is clicked */
  onCreate: () => void;
  /** Callback when refresh is clicked */
  onRefresh: () => void;
  /** Search value */
  searchValue: string;
  /** Callback when search changes */
  onSearchChange: (value: string) => void;
}

export function FeatureFlagTable({
  data,
  isLoading,
  page,
  pageSize,
  onPageChange,
  onToggle,
  onEdit,
  onDelete,
  onCreate,
  onRefresh,
  searchValue,
  onSearchChange,
}: FeatureFlagTableProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const items = data?.items ?? [];
  const total = data?.total ?? 0;
  const totalPages = Math.ceil(total / pageSize);

  const handleDelete = (flag: FeatureFlag) => {
    setDeletingId(flag.id);
    onDelete(flag);
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search feature flags..."
              value={searchValue}
              onChange={(e) => onSearchChange(e.target.value)}
              className="h-10 w-64 rounded-md border border-gray-300 bg-white pl-10 pr-4 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>
          <button
            onClick={onRefresh}
            disabled={isLoading}
            className="flex h-10 items-center gap-2 rounded-md border border-gray-300 bg-white px-4 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </button>
        </div>
        <button
          onClick={onCreate}
          className="flex h-10 items-center gap-2 rounded-md bg-blue-600 px-4 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Plus className="h-4 w-4" />
          Create Flag
        </button>
      </div>

      {/* Table */}
      <div className="overflow-hidden rounded-lg border border-gray-200 bg-white">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Feature Flag
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Status
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Rollout
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Tags
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                Updated
              </th>
              <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                Actions
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white">
            {isLoading && items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center">
                  <div className="flex items-center justify-center gap-2 text-gray-500">
                    <RefreshCw className="h-5 w-5 animate-spin" />
                    Loading feature flags...
                  </div>
                </td>
              </tr>
            ) : items.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-6 py-12 text-center">
                  <div className="flex flex-col items-center gap-2 text-gray-500">
                    <Flag className="h-8 w-8" />
                    <p className="font-medium">No feature flags found</p>
                    <p className="text-sm">Create your first feature flag to get started.</p>
                  </div>
                </td>
              </tr>
            ) : (
              items.map((flag) => (
                <tr key={flag.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${flag.enabled ? "bg-green-100" : "bg-gray-100"}`}>
                        <Flag className={`h-5 w-5 ${flag.enabled ? "text-green-600" : "text-gray-400"}`} />
                      </div>
                      <div>
                        <p className="font-medium text-gray-900">{flag.name}</p>
                        {flag.description && (
                          <p className="text-sm text-gray-500 truncate max-w-xs">
                            {flag.description}
                          </p>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <button
                      onClick={() => onToggle(flag)}
                      className="flex items-center gap-2"
                    >
                      {flag.enabled ? (
                        <>
                          <ToggleRight className="h-6 w-6 text-green-600" />
                          <span className="text-sm font-medium text-green-600">Enabled</span>
                        </>
                      ) : (
                        <>
                          <ToggleLeft className="h-6 w-6 text-gray-400" />
                          <span className="text-sm font-medium text-gray-500">Disabled</span>
                        </>
                      )}
                    </button>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-2">
                      <div className="h-2 w-20 overflow-hidden rounded-full bg-gray-200">
                        <div
                          className="h-full bg-blue-600 transition-all"
                          style={{ width: `${flag.rollout_percentage}%` }}
                        />
                      </div>
                      <span className="text-sm text-gray-600">
                        {flag.rollout_percentage}%
                      </span>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {flag.tags.slice(0, 3).map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600"
                        >
                          {tag}
                        </span>
                      ))}
                      {flag.tags.length > 3 && (
                        <span className="text-xs text-gray-500">
                          +{flag.tags.length - 3} more
                        </span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-500">
                    {format(new Date(flag.updated_at), "MMM d, yyyy")}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => onEdit(flag)}
                        className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                        title="Edit"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(flag)}
                        disabled={deletingId === flag.id}
                        className="rounded p-1 text-gray-400 hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                        title="Delete"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-500">
            Showing {(page - 1) * pageSize + 1} to{" "}
            {Math.min(page * pageSize, total)} of {total} feature flags
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => onPageChange(page - 1)}
              disabled={page === 1}
              className="flex h-8 items-center gap-1 rounded border border-gray-300 bg-white px-3 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              <ChevronLeft className="h-4 w-4" />
              Previous
            </button>
            <span className="text-sm text-gray-600">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
              className="flex h-8 items-center gap-1 rounded border border-gray-300 bg-white px-3 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              Next
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
