/**
 * Audit Components Tests
 *
 * Tests for AuditLogTable, AuditFilters, and AuditEventDetail components.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  AuditLogTable,
  AuditFilters,
  AuditEventDetail,
} from "@/components/audit";
import { AuditAction, AuditSeverity, type AuditEvent } from "@/types/audit";

// ============================================================================
// Test Data
// ============================================================================

const mockAuditEvents: AuditEvent[] = [
  {
    id: "evt-1",
    timestamp: "2024-01-15T10:30:00Z",
    action: AuditAction.LOGIN,
    severity: AuditSeverity.INFO,
    actor_id: "user-123",
    actor_type: "user",
    actor_name: "John Doe",
    resource_id: "session-456",
    resource_type: "session",
    resource_name: "User Session",
    description: "User logged in successfully",
    service_name: "identity-service",
    correlation_id: "corr-789",
    compliance_tags: ["SOC2", "GDPR"],
  },
  {
    id: "evt-2",
    timestamp: "2024-01-15T11:00:00Z",
    action: AuditAction.UPDATE,
    severity: AuditSeverity.WARNING,
    actor_id: "admin-001",
    actor_type: "admin",
    actor_name: "Admin User",
    resource_id: "tenant-abc",
    resource_type: "tenant",
    resource_name: "Acme Corp",
    description: "Tenant configuration updated",
    service_name: "metastore-service",
    correlation_id: "corr-012",
    compliance_tags: ["SOC2"],
  },
];

// ============================================================================
// AuditLogTable Tests
// ============================================================================

describe("AuditLogTable", () => {
  const defaultProps = {
    events: mockAuditEvents,
    total: 100,
    page: 1,
    pageSize: 20,
    isLoading: false,
    onPageChange: vi.fn(),
    onEventClick: vi.fn(),
    onRefresh: vi.fn(),
    onExport: vi.fn(),
    onFilterToggle: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders table", () => {
    render(<AuditLogTable {...defaultProps} />);
    expect(screen.getByRole("table")).toBeInTheDocument();
  });

  it("handles event click on rows", async () => {
    const user = userEvent.setup();
    render(<AuditLogTable {...defaultProps} />);

    // Find and click on a row
    const rows = screen.getAllByRole("row");
    // First row is header, so click second row (first data row)
    await user.click(rows[1]);

    expect(defaultProps.onEventClick).toHaveBeenCalledWith(mockAuditEvents[0]);
  });

  it("shows empty state when no events", () => {
    render(<AuditLogTable {...defaultProps} events={[]} total={0} />);
    expect(screen.getByText(/no audit events found/i)).toBeInTheDocument();
  });

  it("displays pagination info", () => {
    render(<AuditLogTable {...defaultProps} />);
    expect(screen.getByText(/page 1 of 5/i)).toBeInTheDocument();
  });

  it("shows export and filter buttons", () => {
    render(<AuditLogTable {...defaultProps} />);
    expect(screen.getByText(/export/i)).toBeInTheDocument();
    expect(screen.getByText(/filters/i)).toBeInTheDocument();
  });
});

// ============================================================================
// AuditFilters Tests
// ============================================================================

describe("AuditFilters", () => {
  const defaultProps = {
    filters: {},
    onFiltersChange: vi.fn(),
    onClear: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders filter panel", () => {
    render(<AuditFilters {...defaultProps} />);
    expect(screen.getByPlaceholderText(/search/i)).toBeInTheDocument();
    expect(screen.getByText("Filters")).toBeInTheDocument();
  });

  it("calls onClear when clear button is clicked", async () => {
    const user = userEvent.setup();
    render(
      <AuditFilters
        {...defaultProps}
        filters={{ search_text: "test", severity: AuditSeverity.INFO }}
      />
    );

    const clearButton = screen.getByRole("button", { name: /clear/i });
    await user.click(clearButton);

    expect(defaultProps.onClear).toHaveBeenCalled();
  });

  it("shows filter count in clear button", () => {
    render(
      <AuditFilters
        {...defaultProps}
        filters={{
          severity: AuditSeverity.WARNING,
          action: AuditAction.DELETE,
        }}
      />
    );

    // Should show number of active filters
    expect(screen.getByText(/2/)).toBeInTheDocument();
  });
});

// ============================================================================
// AuditEventDetail Tests
// ============================================================================

describe("AuditEventDetail", () => {
  const mockEvent: AuditEvent = mockAuditEvents[0];

  const defaultProps = {
    event: mockEvent,
    open: true,
    onClose: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders event details sheet when open", () => {
    render(<AuditEventDetail {...defaultProps} />);
    expect(screen.getByText("Audit Event Details")).toBeInTheDocument();
  });

  it("displays event description", () => {
    render(<AuditEventDetail {...defaultProps} />);
    expect(screen.getByText(mockEvent.description!)).toBeInTheDocument();
  });

  it("handles null event gracefully", () => {
    const { container } = render(
      <AuditEventDetail event={null} open={true} onClose={vi.fn()} />
    );
    // Should not crash
    expect(container).toBeDefined();
  });
});
