/**
 * Audit Log Table Component
 *
 * Displays audit events in a paginated, sortable table with
 * filtering capabilities.
 */
"use client";

import { formatDistanceToNow, format } from "date-fns";
import {
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  Eye,
  Filter,
  RefreshCw,
  Download,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Skeleton } from "@/components/ui/skeleton";

import type { AuditEvent } from "@/types/audit";
import {
  severityVariants,
  severityColors,
  actionLabels,
  severityLabels,
} from "@/types/audit";

// ============================================================================
// Types
// ============================================================================

interface AuditLogTableProps {
  events: AuditEvent[];
  total: number;
  page: number;
  pageSize: number;
  isLoading?: boolean;
  onPageChange: (page: number) => void;
  onPageSizeChange?: (pageSize: number) => void;
  onEventClick?: (event: AuditEvent) => void;
  onRefresh?: () => void;
  onExport?: () => void;
  onFilterToggle?: () => void;
}

// ============================================================================
// Sub-components
// ============================================================================

function SeverityBadge({ severity }: { severity: AuditEvent["severity"] }) {
  return (
    <Badge
      variant={severityVariants[severity]}
      className={cn("text-xs", severityColors[severity])}
    >
      {severityLabels[severity]}
    </Badge>
  );
}

function ActionBadge({ action }: { action: AuditEvent["action"] }) {
  return (
    <Badge variant="outline" className="text-xs font-normal">
      {actionLabels[action]}
    </Badge>
  );
}

function TimestampCell({ timestamp }: { timestamp: string }) {
  const date = new Date(timestamp);
  const relative = formatDistanceToNow(date, { addSuffix: true });
  const absolute = format(date, "PPpp");

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span className="text-sm text-muted-foreground cursor-help">
            {relative}
          </span>
        </TooltipTrigger>
        <TooltipContent>
          <p>{absolute}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

function TableSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center space-x-4 p-4">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-4 w-20" />
          <Skeleton className="h-4 w-40" />
          <Skeleton className="h-4 w-24" />
        </div>
      ))}
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export function AuditLogTable({
  events,
  total,
  page,
  pageSize,
  isLoading = false,
  onPageChange,
  onPageSizeChange: _onPageSizeChange,  // TODO: Implement page size selector
  onEventClick,
  onRefresh,
  onExport,
  onFilterToggle,
}: AuditLogTableProps) {
  const totalPages = Math.ceil(total / pageSize);
  const startIndex = (page - 1) * pageSize + 1;
  const endIndex = Math.min(page * pageSize, total);

  const canGoBack = page > 1;
  const canGoForward = page < totalPages;

  if (isLoading && events.length === 0) {
    return <TableSkeleton />;
  }

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {onFilterToggle && (
            <Button
              variant="outline"
              size="sm"
              onClick={onFilterToggle}
              className="h-8"
            >
              <Filter className="h-4 w-4 mr-2" />
              Filters
            </Button>
          )}
          {onRefresh && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onRefresh}
              disabled={isLoading}
              className="h-8"
            >
              <RefreshCw
                className={cn("h-4 w-4", isLoading && "animate-spin")}
              />
            </Button>
          )}
        </div>

        <div className="flex items-center gap-2">
          {onExport && (
            <Button
              variant="outline"
              size="sm"
              onClick={onExport}
              className="h-8"
            >
              <Download className="h-4 w-4 mr-2" />
              Export
            </Button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[140px]">Time</TableHead>
              <TableHead className="w-[100px]">Severity</TableHead>
              <TableHead className="w-[100px]">Action</TableHead>
              <TableHead>Actor</TableHead>
              <TableHead>Resource</TableHead>
              <TableHead className="w-[150px]">Service</TableHead>
              <TableHead className="w-[50px]"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {events.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={7}
                  className="h-24 text-center text-muted-foreground"
                >
                  No audit events found.
                </TableCell>
              </TableRow>
            ) : (
              events.map((event) => (
                <TableRow
                  key={event.id}
                  className={cn(
                    "cursor-pointer hover:bg-muted/50",
                    event.severity === "ERROR" && "bg-red-50/50 dark:bg-red-950/20",
                    event.severity === "CRITICAL" && "bg-red-100/50 dark:bg-red-900/30"
                  )}
                  onClick={() => onEventClick?.(event)}
                >
                  <TableCell>
                    <TimestampCell timestamp={event.timestamp} />
                  </TableCell>
                  <TableCell>
                    <SeverityBadge severity={event.severity} />
                  </TableCell>
                  <TableCell>
                    <ActionBadge action={event.action} />
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-col">
                      <span className="font-medium text-sm">
                        {event.actor_name || event.actor_id}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {event.actor_type}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="flex flex-col">
                      <span className="font-medium text-sm">
                        {event.resource_name || event.resource_id}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {event.resource_type}
                      </span>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-muted-foreground">
                      {event.service_name}
                    </span>
                  </TableCell>
                  <TableCell>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8"
                      onClick={(e) => {
                        e.stopPropagation();
                        onEventClick?.(event);
                      }}
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      <div className="flex items-center justify-between px-2">
        <div className="text-sm text-muted-foreground">
          {total > 0 ? (
            <>
              Showing {startIndex} to {endIndex} of {total} events
            </>
          ) : (
            "No events"
          )}
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => onPageChange(1)}
            disabled={!canGoBack || isLoading}
          >
            <ChevronsLeft className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => onPageChange(page - 1)}
            disabled={!canGoBack || isLoading}
          >
            <ChevronLeft className="h-4 w-4" />
          </Button>

          <span className="text-sm px-2">
            Page {page} of {totalPages || 1}
          </span>

          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => onPageChange(page + 1)}
            disabled={!canGoForward || isLoading}
          >
            <ChevronRight className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            className="h-8 w-8"
            onClick={() => onPageChange(totalPages)}
            disabled={!canGoForward || isLoading}
          >
            <ChevronsRight className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  );
}

export default AuditLogTable;
