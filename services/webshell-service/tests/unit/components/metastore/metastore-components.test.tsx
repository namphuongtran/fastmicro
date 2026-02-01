/**
 * Unit tests for Metastore components
 *
 * Tests feature flag table and form components
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { FeatureFlagTable, FeatureFlagForm } from "@/components/metastore";
import type { FeatureFlag, PaginatedFeatureFlags } from "@/types/metastore";

// Test data factory
function createTestFeatureFlag(overrides: Partial<FeatureFlag> = {}): FeatureFlag {
  return {
    id: "ff-001",
    name: "test-feature",
    description: "Test feature flag description",
    enabled: true,
    default_value: true,
    rollout_percentage: 100,
    targeting_rules: [],
    tenant_overrides: {},
    environment_overrides: {
      development: null,
      staging: null,
      production: null,
      test: null,
    },
    expires_at: null,
    tags: ["test", "feature"],
    created_at: "2025-01-01T00:00:00Z",
    updated_at: "2025-01-15T12:00:00Z",
    created_by: null,
    updated_by: null,
    ...overrides,
  };
}

function createTestFlagsResponse(count: number = 3): PaginatedFeatureFlags {
  const flags: FeatureFlag[] = [];
  for (let i = 0; i < count; i++) {
    flags.push(createTestFeatureFlag({
      id: `ff-${String(i + 1).padStart(3, "0")}`,
      name: `feature-${i + 1}`,
      description: `Description for feature ${i + 1}`,
      enabled: i % 2 === 0,
    }));
  }
  return {
    items: flags,
    total: count,
    page: 1,
    page_size: 20,
    total_pages: Math.ceil(count / 20),
  };
}

// Query client wrapper
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        {children}
      </QueryClientProvider>
    );
  };
}

describe("FeatureFlagTable", () => {
  const defaultProps = {
    data: undefined as PaginatedFeatureFlags | undefined,
    isLoading: false,
    page: 1,
    pageSize: 20,
    onPageChange: vi.fn(),
    onToggle: vi.fn(),
    onEdit: vi.fn(),
    onDelete: vi.fn(),
    onCreate: vi.fn(),
    onRefresh: vi.fn(),
    searchValue: "",
    onSearchChange: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Loading State", () => {
    it("should render loading message when isLoading is true", () => {
      render(
        <FeatureFlagTable {...defaultProps} isLoading={true} />,
        { wrapper: createWrapper() }
      );

      // Should show loading text
      expect(screen.getByText(/loading feature flags/i)).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should render empty state when no data", () => {
      render(
        <FeatureFlagTable 
          {...defaultProps} 
          data={{ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 }} 
        />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText(/no feature flags found/i)).toBeInTheDocument();
    });

    it("should show create button in empty state", () => {
      render(
        <FeatureFlagTable 
          {...defaultProps} 
          data={{ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 }} 
        />,
        { wrapper: createWrapper() }
      );

      const createButtons = screen.getAllByRole("button", { name: /create/i });
      expect(createButtons.length).toBeGreaterThan(0);
    });
  });

  describe("Data Rendering", () => {
    it("should render feature flags in table", () => {
      const data = createTestFlagsResponse(3);
      
      render(
        <FeatureFlagTable {...defaultProps} data={data} />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText("feature-1")).toBeInTheDocument();
      expect(screen.getByText("feature-2")).toBeInTheDocument();
      expect(screen.getByText("feature-3")).toBeInTheDocument();
    });

    it("should render flag descriptions", () => {
      const data = createTestFlagsResponse(1);
      
      render(
        <FeatureFlagTable {...defaultProps} data={data} />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText("Description for feature 1")).toBeInTheDocument();
    });

    it("should show enabled/disabled status", () => {
      const data = createTestFlagsResponse(2);
      
      render(
        <FeatureFlagTable {...defaultProps} data={data} />,
        { wrapper: createWrapper() }
      );

      // First flag is enabled (i % 2 === 0), second is disabled
      // Table shows "Enabled" or "Disabled" text
      expect(screen.getByText("Enabled")).toBeInTheDocument();
      expect(screen.getByText("Disabled")).toBeInTheDocument();
    });
  });

  describe("Actions", () => {
    it("should call onToggle when toggle button is clicked", async () => {
      const data = createTestFlagsResponse(1);
      const onToggle = vi.fn();
      
      render(
        <FeatureFlagTable {...defaultProps} data={data} onToggle={onToggle} />,
        { wrapper: createWrapper() }
      );

      // Click on the status toggle button (shows "Enabled" since first flag is enabled)
      const toggleButton = screen.getByText("Enabled").closest("button");
      expect(toggleButton).toBeTruthy();
      await userEvent.click(toggleButton!);

      expect(onToggle).toHaveBeenCalledWith(data.items[0]);
    });

    it("should call onCreate when create button is clicked", async () => {
      const data = createTestFlagsResponse(1);
      const onCreate = vi.fn();
      
      render(
        <FeatureFlagTable {...defaultProps} data={data} onCreate={onCreate} />,
        { wrapper: createWrapper() }
      );

      const createButton = screen.getByRole("button", { name: /create/i });
      await userEvent.click(createButton);

      expect(onCreate).toHaveBeenCalled();
    });

    it("should call onRefresh when refresh button is clicked", async () => {
      const data = createTestFlagsResponse(1);
      const onRefresh = vi.fn();
      
      render(
        <FeatureFlagTable {...defaultProps} data={data} onRefresh={onRefresh} />,
        { wrapper: createWrapper() }
      );

      const refreshButton = screen.getByRole("button", { name: /refresh/i });
      await userEvent.click(refreshButton);

      expect(onRefresh).toHaveBeenCalled();
    });

    it("should call onSearchChange when search input changes", async () => {
      const data = createTestFlagsResponse(1);
      const onSearchChange = vi.fn();
      
      render(
        <FeatureFlagTable {...defaultProps} data={data} onSearchChange={onSearchChange} />,
        { wrapper: createWrapper() }
      );

      const searchInput = screen.getByPlaceholderText(/search/i);
      await userEvent.type(searchInput, "test");

      expect(onSearchChange).toHaveBeenCalled();
    });
  });

  describe("Pagination", () => {
    it("should show pagination when multiple pages exist", () => {
      const data: PaginatedFeatureFlags = {
        items: [createTestFeatureFlag()],
        total: 100,
        page: 1,
        page_size: 20,
        total_pages: 5,
      };
      
      render(
        <FeatureFlagTable {...defaultProps} data={data} />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText(/page 1 of 5/i)).toBeInTheDocument();
    });

    it("should call onPageChange when next page is clicked", async () => {
      const data: PaginatedFeatureFlags = {
        items: [createTestFeatureFlag()],
        total: 100,
        page: 1,
        page_size: 20,
        total_pages: 5,
      };
      const onPageChange = vi.fn();
      
      render(
        <FeatureFlagTable {...defaultProps} data={data} onPageChange={onPageChange} />,
        { wrapper: createWrapper() }
      );

      const nextButton = screen.getByRole("button", { name: /next/i });
      await userEvent.click(nextButton);

      expect(onPageChange).toHaveBeenCalledWith(2);
    });
  });
});

describe("FeatureFlagForm", () => {
  const defaultProps = {
    flag: undefined as FeatureFlag | undefined,
    isOpen: true,
    onClose: vi.fn(),
    onSubmit: vi.fn(),
    isSubmitting: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Create Mode", () => {
    it("should render empty form for new flag", () => {
      render(
        <FeatureFlagForm {...defaultProps} />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText(/create feature flag/i)).toBeInTheDocument();
    });

    it("should have empty name input", () => {
      render(
        <FeatureFlagForm {...defaultProps} />,
        { wrapper: createWrapper() }
      );

      const nameInput = screen.getByPlaceholderText(/my-feature-flag/i);
      expect(nameInput).toHaveValue("");
    });

    it("should require name field", async () => {
      const onSubmit = vi.fn();
      
      render(
        <FeatureFlagForm {...defaultProps} onSubmit={onSubmit} />,
        { wrapper: createWrapper() }
      );

      const submitButton = screen.getByRole("button", { name: /create/i });
      await userEvent.click(submitButton);

      // Form should not submit without name (button is disabled)
      expect(onSubmit).not.toHaveBeenCalled();
    });

    it("should call onSubmit with form data", async () => {
      const onSubmit = vi.fn();
      
      render(
        <FeatureFlagForm {...defaultProps} onSubmit={onSubmit} />,
        { wrapper: createWrapper() }
      );

      // Fill in the form
      const nameInput = screen.getByPlaceholderText(/my-feature-flag/i);
      await userEvent.type(nameInput, "new-feature");

      const descInput = screen.getByPlaceholderText(/describe what this feature flag controls/i);
      await userEvent.type(descInput, "New feature description");

      const submitButton = screen.getByRole("button", { name: /create/i });
      await userEvent.click(submitButton);

      await waitFor(() => {
        expect(onSubmit).toHaveBeenCalledWith(
          expect.objectContaining({
            name: "new-feature",
            description: "New feature description",
          })
        );
      });
    });
  });

  describe("Edit Mode", () => {
    const existingFlag = createTestFeatureFlag({
      name: "existing-feature",
      description: "Existing description",
      enabled: true,
      default_value: false,
    });

    it("should show edit title", () => {
      render(
        <FeatureFlagForm {...defaultProps} flag={existingFlag} />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText(/edit feature flag/i)).toBeInTheDocument();
    });

    it("should populate form with existing values", () => {
      render(
        <FeatureFlagForm {...defaultProps} flag={existingFlag} />,
        { wrapper: createWrapper() }
      );

      const nameInput = screen.getByPlaceholderText(/my-feature-flag/i);
      expect(nameInput).toHaveValue("existing-feature");

      const descInput = screen.getByPlaceholderText(/describe what this feature flag controls/i);
      expect(descInput).toHaveValue("Existing description");
    });

    it("should show update button instead of create", () => {
      render(
        <FeatureFlagForm {...defaultProps} flag={existingFlag} />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByRole("button", { name: /update/i })).toBeInTheDocument();
    });
  });

  describe("Closed State", () => {
    it("should not render when isOpen is false", () => {
      render(
        <FeatureFlagForm {...defaultProps} isOpen={false} />,
        { wrapper: createWrapper() }
      );

      expect(screen.queryByText(/create feature flag/i)).not.toBeInTheDocument();
    });
  });

  describe("Submitting State", () => {
    it("should disable submit button when submitting", () => {
      render(
        <FeatureFlagForm {...defaultProps} isSubmitting={true} />,
        { wrapper: createWrapper() }
      );

      const submitButton = screen.getByRole("button", { name: /saving/i });
      expect(submitButton).toBeDisabled();
    });

    it("should show loading state on button", () => {
      render(
        <FeatureFlagForm {...defaultProps} isSubmitting={true} />,
        { wrapper: createWrapper() }
      );

      expect(screen.getByText(/saving/i)).toBeInTheDocument();
    });
  });

  describe("Close Action", () => {
    it("should call onClose when cancel button is clicked", async () => {
      const onClose = vi.fn();
      
      render(
        <FeatureFlagForm {...defaultProps} onClose={onClose} />,
        { wrapper: createWrapper() }
      );

      const cancelButton = screen.getByRole("button", { name: /cancel/i });
      await userEvent.click(cancelButton);

      expect(onClose).toHaveBeenCalled();
    });
  });
});
