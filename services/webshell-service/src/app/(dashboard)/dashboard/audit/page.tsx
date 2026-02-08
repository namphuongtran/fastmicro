/**
 * Audit Logs Page
 *
 * Main page for viewing and searching audit logs.
 * Features filtering, pagination, and detailed event view.
 */
"use client";

import { useState, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { FileText, Shield, AlertTriangle } from "lucide-react";

import { useAuditEvents } from "@/hooks/use-audit";
import {
  AuditLogTable,
  AuditFilters,
  AuditEventDetail,
} from "@/components/audit";
import { auditQueryKeys } from "@/services/audit-api";
import type { AuditEvent, AuditQueryParams } from "@/types/audit";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

// ============================================================================
// Constants
// ============================================================================

const DEFAULT_PAGE_SIZE = 20;

// ============================================================================
// Page Component
// ============================================================================

export default function AuditLogsPage() {
  // Filter state
  const [filters, setFilters] = useState<AuditQueryParams>({
    page: 1,
    page_size: DEFAULT_PAGE_SIZE,
  });
  const [showFilters, setShowFilters] = useState(false);

  // Selected event for detail view
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);

  // Query client for manual refetch
  const queryClient = useQueryClient();

  // Fetch audit events
  const {
    data: auditData,
    isLoading,
    isError,
    error,
    isFetching,
  } = useAuditEvents(filters);

  // Handlers
  const handlePageChange = useCallback((page: number) => {
    setFilters((prev) => ({ ...prev, page }));
  }, []);

  const handleFiltersChange = useCallback((newFilters: AuditQueryParams) => {
    setFilters((prev) => ({
      ...newFilters,
      page: 1, // Reset to first page on filter change
      page_size: prev.page_size,
    }));
  }, []);

  const handleClearFilters = useCallback(() => {
    setFilters({
      page: 1,
      page_size: DEFAULT_PAGE_SIZE,
    });
  }, []);

  const handleRefresh = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: auditQueryKeys.lists() });
  }, [queryClient]);

  const handleExport = useCallback(() => {
    // TODO: Implement export functionality
    console.log("Export audit logs with filters:", filters);
  }, [filters]);

  const handleEventClick = useCallback((event: AuditEvent) => {
    setSelectedEvent(event);
  }, []);

  const handleCloseDetail = useCallback(() => {
    setSelectedEvent(null);
  }, []);

  // Error state
  if (isError) {
    return (
      <div className="container py-6">
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertTitle>Error Loading Audit Logs</AlertTitle>
          <AlertDescription>
            {error instanceof Error
              ? error.message
              : "An unexpected error occurred while loading audit logs."}
          </AlertDescription>
        </Alert>
      </div>
    );
  }

  return (
    <div className="container py-6 space-y-6">
      {/* Page Header */}
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-2">
          <Shield className="h-6 w-6 text-primary" />
          <h1 className="text-2xl font-bold tracking-tight">Audit Logs</h1>
        </div>
        <p className="text-muted-foreground">
          Monitor system activity, track user actions, and maintain compliance
          with detailed audit trails.
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Events</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {auditData?.total.toLocaleString() ?? "—"}
            </div>
            <p className="text-xs text-muted-foreground">
              Matching current filters
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Current Page
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {filters.page} / {Math.ceil((auditData?.total ?? 0) / DEFAULT_PAGE_SIZE) || 1}
            </div>
            <p className="text-xs text-muted-foreground">
              {DEFAULT_PAGE_SIZE} events per page
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              Active Filters
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {
                [
                  filters.severity,
                  filters.action,
                  filters.resource_type,
                  filters.actor_id,
                  filters.start_date,
                  filters.end_date,
                  filters.search_text,
                ].filter(Boolean).length
              }
            </div>
            <p className="text-xs text-muted-foreground">
              {showFilters ? "Filters panel open" : "Click Filters to modify"}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <AuditFilters
          filters={filters}
          onFiltersChange={handleFiltersChange}
          onClear={handleClearFilters}
        />
      )}

      {/* Audit Log Table */}
      <Card>
        <CardHeader>
          <CardTitle>Event History</CardTitle>
          <CardDescription>
            Click on any event to view detailed information.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <AuditLogTable
            events={auditData?.items ?? []}
            total={auditData?.total ?? 0}
            page={filters.page ?? 1}
            pageSize={filters.page_size ?? DEFAULT_PAGE_SIZE}
            isLoading={isLoading || isFetching}
            onPageChange={handlePageChange}
            onEventClick={handleEventClick}
            onRefresh={handleRefresh}
            onExport={handleExport}
            onFilterToggle={() => setShowFilters((prev) => !prev)}
          />
        </CardContent>
      </Card>

      {/* Event Detail Panel */}
      <AuditEventDetail
        event={selectedEvent}
        open={!!selectedEvent}
        onClose={handleCloseDetail}
      />
    </div>
  );
}
