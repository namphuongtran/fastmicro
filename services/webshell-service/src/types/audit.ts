/**
 * Audit Types
 *
 * Type definitions for audit log functionality.
 * These types mirror the backend audit-service API models.
 */

// ============================================================================
// Enums
// ============================================================================

/**
 * Audit action types - matches backend AuditAction enum
 */
export const AuditAction = {
  CREATE: "CREATE",
  READ: "READ",
  UPDATE: "UPDATE",
  DELETE: "DELETE",
  LOGIN: "LOGIN",
  LOGOUT: "LOGOUT",
  EXPORT: "EXPORT",
  IMPORT: "IMPORT",
  APPROVE: "APPROVE",
  REJECT: "REJECT",
  SUBMIT: "SUBMIT",
  CANCEL: "CANCEL",
  EXECUTE: "EXECUTE",
  CONFIGURE: "CONFIGURE",
  GRANT: "GRANT",
  REVOKE: "REVOKE",
} as const;

export type AuditAction = (typeof AuditAction)[keyof typeof AuditAction];

/**
 * Audit severity levels - matches backend AuditSeverity enum
 */
export const AuditSeverity = {
  DEBUG: "DEBUG",
  INFO: "INFO",
  WARNING: "WARNING",
  ERROR: "ERROR",
  CRITICAL: "CRITICAL",
} as const;

export type AuditSeverity = (typeof AuditSeverity)[keyof typeof AuditSeverity];

// ============================================================================
// API Request/Response Types
// ============================================================================

/**
 * Audit event response from the API
 */
export interface AuditEvent {
  id: string;
  timestamp: string;
  service_name: string;
  correlation_id: string | null;
  actor_id: string;
  actor_type: string;
  actor_name: string | null;
  action: AuditAction;
  severity: AuditSeverity;
  resource_type: string;
  resource_id: string;
  resource_name: string | null;
  description: string | null;
  compliance_tags: string[];
}

/**
 * Paginated response for audit events
 */
export interface PaginatedAuditEvents {
  items: AuditEvent[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

/**
 * Filters for querying audit events
 */
export interface AuditFilters {
  actor_id?: string;
  resource_type?: string;
  action?: AuditAction;
  severity?: AuditSeverity;
  start_date?: string;
  end_date?: string;
  search_text?: string;
}

/**
 * Query parameters for listing audit events
 */
export interface AuditQueryParams extends AuditFilters {
  page?: number;
  page_size?: number;
}

// ============================================================================
// UI Helper Types
// ============================================================================

/**
 * Severity badge variant mapping
 */
export const severityVariants: Record<AuditSeverity, "default" | "secondary" | "destructive" | "outline"> = {
  DEBUG: "secondary",
  INFO: "default",
  WARNING: "outline",
  ERROR: "destructive",
  CRITICAL: "destructive",
};

/**
 * Severity color mapping for badges and indicators
 */
export const severityColors: Record<AuditSeverity, string> = {
  DEBUG: "text-muted-foreground",
  INFO: "text-blue-600 dark:text-blue-400",
  WARNING: "text-yellow-600 dark:text-yellow-400",
  ERROR: "text-red-600 dark:text-red-400",
  CRITICAL: "text-red-700 dark:text-red-300 font-bold",
};

/**
 * Action icon mapping
 */
export const actionIcons: Record<AuditAction, string> = {
  CREATE: "plus",
  READ: "eye",
  UPDATE: "pencil",
  DELETE: "trash-2",
  LOGIN: "log-in",
  LOGOUT: "log-out",
  EXPORT: "download",
  IMPORT: "upload",
  APPROVE: "check-circle",
  REJECT: "x-circle",
  SUBMIT: "send",
  CANCEL: "x",
  EXECUTE: "play",
  CONFIGURE: "settings",
  GRANT: "key",
  REVOKE: "key-off",
};

/**
 * Human-readable labels for actions
 */
export const actionLabels: Record<AuditAction, string> = {
  CREATE: "Created",
  READ: "Viewed",
  UPDATE: "Updated",
  DELETE: "Deleted",
  LOGIN: "Logged In",
  LOGOUT: "Logged Out",
  EXPORT: "Exported",
  IMPORT: "Imported",
  APPROVE: "Approved",
  REJECT: "Rejected",
  SUBMIT: "Submitted",
  CANCEL: "Cancelled",
  EXECUTE: "Executed",
  CONFIGURE: "Configured",
  GRANT: "Granted Access",
  REVOKE: "Revoked Access",
};

/**
 * Human-readable labels for severity levels
 */
export const severityLabels: Record<AuditSeverity, string> = {
  DEBUG: "Debug",
  INFO: "Info",
  WARNING: "Warning",
  ERROR: "Error",
  CRITICAL: "Critical",
};
