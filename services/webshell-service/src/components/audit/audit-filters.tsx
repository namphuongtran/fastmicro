/**
 * Audit Log Filters Component
 *
 * Filter panel for audit log queries with date range,
 * severity, action, and text search.
 */
"use client";

import { useState } from "react";
import { format } from "date-fns";
import { CalendarIcon, X, Search } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Calendar } from "@/components/ui/calendar";
import { Badge } from "@/components/ui/badge";

import type { AuditQueryParams, AuditAction, AuditSeverity } from "@/types/audit";
import {
  AuditAction as AuditActionEnum,
  AuditSeverity as AuditSeverityEnum,
  actionLabels,
  severityLabels,
} from "@/types/audit";

// ============================================================================
// Types
// ============================================================================

interface AuditFiltersProps {
  filters: AuditQueryParams;
  onFiltersChange: (filters: AuditQueryParams) => void;
  onClear?: () => void;
  className?: string;
}

// ============================================================================
// Component
// ============================================================================

export function AuditFilters({
  filters,
  onFiltersChange,
  onClear,
  className,
}: AuditFiltersProps) {
  const [searchInput, setSearchInput] = useState(filters.search_text ?? "");

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onFiltersChange({ ...filters, search_text: searchInput || undefined });
  };

  const handleSeverityChange = (value: string) => {
    onFiltersChange({
      ...filters,
      severity: value === "all" ? undefined : (value as AuditSeverity),
    });
  };

  const handleActionChange = (value: string) => {
    onFiltersChange({
      ...filters,
      action: value === "all" ? undefined : (value as AuditAction),
    });
  };

  const handleStartDateChange = (date: Date | undefined) => {
    onFiltersChange({
      ...filters,
      start_date: date ? date.toISOString() : undefined,
    });
  };

  const handleEndDateChange = (date: Date | undefined) => {
    onFiltersChange({
      ...filters,
      end_date: date ? date.toISOString() : undefined,
    });
  };

  const handleResourceTypeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFiltersChange({
      ...filters,
      resource_type: e.target.value || undefined,
    });
  };

  const handleActorIdChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onFiltersChange({
      ...filters,
      actor_id: e.target.value || undefined,
    });
  };

  const activeFilterCount = [
    filters.severity,
    filters.action,
    filters.start_date,
    filters.end_date,
    filters.resource_type,
    filters.actor_id,
    filters.search_text,
  ].filter(Boolean).length;

  const handleClearAll = () => {
    setSearchInput("");
    onClear?.();
  };

  return (
    <div className={cn("space-y-4 p-4 border rounded-lg bg-card", className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Filters</h3>
        {activeFilterCount > 0 && (
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearAll}
            className="h-7 text-xs"
          >
            <X className="h-3 w-3 mr-1" />
            Clear ({activeFilterCount})
          </Button>
        )}
      </div>

      {/* Search */}
      <form onSubmit={handleSearchSubmit}>
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            type="search"
            placeholder="Search audit logs..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            className="pl-8"
          />
        </div>
      </form>

      {/* Filter Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {/* Severity */}
        <div className="space-y-2">
          <Label htmlFor="severity" className="text-xs">
            Severity
          </Label>
          <Select
            value={filters.severity ?? "all"}
            onValueChange={handleSeverityChange}
          >
            <SelectTrigger id="severity">
              <SelectValue placeholder="All severities" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All severities</SelectItem>
              {Object.entries(AuditSeverityEnum).map(([key, value]) => (
                <SelectItem key={key} value={value}>
                  {severityLabels[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Action */}
        <div className="space-y-2">
          <Label htmlFor="action" className="text-xs">
            Action
          </Label>
          <Select
            value={filters.action ?? "all"}
            onValueChange={handleActionChange}
          >
            <SelectTrigger id="action">
              <SelectValue placeholder="All actions" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All actions</SelectItem>
              {Object.entries(AuditActionEnum).map(([key, value]) => (
                <SelectItem key={key} value={value}>
                  {actionLabels[value]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Resource Type */}
        <div className="space-y-2">
          <Label htmlFor="resource-type" className="text-xs">
            Resource Type
          </Label>
          <Input
            id="resource-type"
            placeholder="e.g., user, project"
            value={filters.resource_type ?? ""}
            onChange={handleResourceTypeChange}
          />
        </div>

        {/* Actor ID */}
        <div className="space-y-2">
          <Label htmlFor="actor-id" className="text-xs">
            Actor ID
          </Label>
          <Input
            id="actor-id"
            placeholder="User or service ID"
            value={filters.actor_id ?? ""}
            onChange={handleActorIdChange}
          />
        </div>

        {/* Start Date */}
        <div className="space-y-2">
          <Label className="text-xs">Start Date</Label>
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className={cn(
                  "w-full justify-start text-left font-normal",
                  !filters.start_date && "text-muted-foreground"
                )}
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {filters.start_date
                  ? format(new Date(filters.start_date), "PPP")
                  : "Pick a date"}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={
                  filters.start_date ? new Date(filters.start_date) : undefined
                }
                onSelect={handleStartDateChange}
                initialFocus
              />
            </PopoverContent>
          </Popover>
        </div>

        {/* End Date */}
        <div className="space-y-2">
          <Label className="text-xs">End Date</Label>
          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                className={cn(
                  "w-full justify-start text-left font-normal",
                  !filters.end_date && "text-muted-foreground"
                )}
              >
                <CalendarIcon className="mr-2 h-4 w-4" />
                {filters.end_date
                  ? format(new Date(filters.end_date), "PPP")
                  : "Pick a date"}
              </Button>
            </PopoverTrigger>
            <PopoverContent className="w-auto p-0" align="start">
              <Calendar
                mode="single"
                selected={
                  filters.end_date ? new Date(filters.end_date) : undefined
                }
                onSelect={handleEndDateChange}
                initialFocus
              />
            </PopoverContent>
          </Popover>
        </div>
      </div>

      {/* Active Filters Summary */}
      {activeFilterCount > 0 && (
        <div className="flex flex-wrap gap-2 pt-2 border-t">
          {filters.severity && (
            <Badge variant="secondary" className="text-xs">
              Severity: {severityLabels[filters.severity]}
            </Badge>
          )}
          {filters.action && (
            <Badge variant="secondary" className="text-xs">
              Action: {actionLabels[filters.action]}
            </Badge>
          )}
          {filters.resource_type && (
            <Badge variant="secondary" className="text-xs">
              Resource: {filters.resource_type}
            </Badge>
          )}
          {filters.actor_id && (
            <Badge variant="secondary" className="text-xs">
              Actor: {filters.actor_id}
            </Badge>
          )}
          {filters.start_date && (
            <Badge variant="secondary" className="text-xs">
              From: {format(new Date(filters.start_date), "PP")}
            </Badge>
          )}
          {filters.end_date && (
            <Badge variant="secondary" className="text-xs">
              To: {format(new Date(filters.end_date), "PP")}
            </Badge>
          )}
          {filters.search_text && (
            <Badge variant="secondary" className="text-xs">
              Search: &quot;{filters.search_text}&quot;
            </Badge>
          )}
        </div>
      )}
    </div>
  );
}

export default AuditFilters;
