"use client";

import React, {
  createContext,
  useContext,
  useState,
  useCallback,
  useMemo,
  useEffect,
} from "react";
import { useSession } from "next-auth/react";

/**
 * Multi-Tenant Context Provider
 *
 * This context manages the current tenant selection across the application.
 * It integrates with the authentication system to:
 * 1. Read available tenants from the user's JWT claims
 * 2. Persist tenant selection in localStorage
 * 3. Provide tenant switching functionality
 * 4. Include tenant ID in API requests via headers
 *
 * JWT Claim Structure (from Identity Service):
 * {
 *   "sub": "user-uuid",
 *   "tid": "current-tenant-id",  // Current tenant
 *   "tenants": [                 // Available tenants
 *     { "id": "tenant-1", "name": "Tenant One", "role": "admin" },
 *     { "id": "tenant-2", "name": "Tenant Two", "role": "member" }
 *   ]
 * }
 */

// Storage key for tenant persistence
const TENANT_STORAGE_KEY = "webshell_current_tenant_id";

/**
 * Tenant information structure
 */
export interface Tenant {
  id: string;
  name: string;
  slug?: string;
  role?: string;
  permissions?: string[];
}

/**
 * Tenant context state
 */
export interface TenantContextState {
  /** Currently selected tenant */
  currentTenant: Tenant | null;
  /** All tenants the user has access to */
  availableTenants: Tenant[];
  /** Whether tenant data is being loaded */
  isLoading: boolean;
  /** Error message if tenant loading failed */
  error: string | null;
  /** Switch to a different tenant */
  switchTenant: (tenantId: string) => Promise<void>;
  /** Refresh tenant list from server */
  refreshTenants: () => Promise<void>;
  /** Check if user has a specific permission in current tenant */
  hasPermission: (permission: string) => boolean;
  /** Check if user has a specific role in current tenant */
  hasRole: (role: string) => boolean;
}

const TenantContext = createContext<TenantContextState | null>(null);

/**
 * Get stored tenant ID from localStorage
 */
function getStoredTenantId(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(TENANT_STORAGE_KEY);
  } catch {
    return null;
  }
}

/**
 * Store tenant ID in localStorage
 */
function setStoredTenantId(tenantId: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (tenantId) {
      localStorage.setItem(TENANT_STORAGE_KEY, tenantId);
    } else {
      localStorage.removeItem(TENANT_STORAGE_KEY);
    }
  } catch {
    // Ignore storage errors (e.g., private browsing)
  }
}

interface TenantProviderProps {
  children: React.ReactNode;
  /** Default tenant ID to use if none is stored */
  defaultTenantId?: string;
}

/**
 * Tenant Provider Component
 *
 * Provides multi-tenant context to the application.
 * Must be wrapped inside AuthProvider/SessionProvider.
 */
export function TenantProvider({
  children,
  defaultTenantId,
}: TenantProviderProps) {
  const { data: session, status } = useSession();

  const [currentTenant, setCurrentTenant] = useState<Tenant | null>(null);
  const [availableTenants, setAvailableTenants] = useState<Tenant[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  /**
   * Extract tenants from session/JWT claims
   * In a real implementation, this would come from the JWT or an API call
   */
  const extractTenantsFromSession = useCallback((): Tenant[] => {
    if (!session?.user) return [];

    // For now, create a default tenant based on the user
    // In production, this would come from the JWT 'tenants' claim
    // or from an API call to get user's tenant memberships
    const defaultTenant: Tenant = {
      id: defaultTenantId || "default",
      name: "Default Tenant",
      role: "admin",
      permissions: ["read", "write", "admin"],
    };

    // TODO: When Identity Service includes tenants in JWT:
    // const tenants = (session as any).tenants as Tenant[] || [];
    // return tenants;

    return [defaultTenant];
  }, [session, defaultTenantId]);

  /**
   * Initialize tenant state when session changes
   */
  useEffect(() => {
    if (status === "loading") {
      return;
    }

    if (status === "unauthenticated") {
      setCurrentTenant(null);
      setAvailableTenants([]);
      setIsLoading(false);
      setStoredTenantId(null);
      return;
    }

    // User is authenticated
    const tenants = extractTenantsFromSession();
    setAvailableTenants(tenants);

    // Determine which tenant to select
    const storedTenantId = getStoredTenantId();
    let selectedTenant: Tenant | null = null;

    if (storedTenantId) {
      // Try to find the stored tenant
      selectedTenant = tenants.find((t) => t.id === storedTenantId) || null;
    }

    if (!selectedTenant && tenants.length > 0) {
      // Fall back to first available tenant
      selectedTenant = tenants[0];
    }

    setCurrentTenant(selectedTenant);
    if (selectedTenant) {
      setStoredTenantId(selectedTenant.id);
    }

    setIsLoading(false);
  }, [status, extractTenantsFromSession]);

  /**
   * Switch to a different tenant
   */
  const switchTenant = useCallback(
    async (tenantId: string): Promise<void> => {
      setIsLoading(true);
      setError(null);

      try {
        const tenant = availableTenants.find((t) => t.id === tenantId);
        if (!tenant) {
          throw new Error(`Tenant ${tenantId} not found or not accessible`);
        }

        // In production, you might want to:
        // 1. Call an API to switch tenant context server-side
        // 2. Refresh the user's session/token with the new tenant
        // 3. Invalidate cached data for the old tenant

        setCurrentTenant(tenant);
        setStoredTenantId(tenant.id);

        // Optionally trigger a page reload or data refresh
        // window.location.reload();
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Failed to switch tenant";
        setError(message);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [availableTenants]
  );

  /**
   * Refresh tenant list from server
   */
  const refreshTenants = useCallback(async (): Promise<void> => {
    setIsLoading(true);
    setError(null);

    try {
      // TODO: Call API to refresh tenant list
      // const response = await fetch('/api/tenants');
      // const tenants = await response.json();
      // setAvailableTenants(tenants);

      // For now, re-extract from session
      const tenants = extractTenantsFromSession();
      setAvailableTenants(tenants);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to refresh tenants";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [extractTenantsFromSession]);

  /**
   * Check if user has a specific permission in current tenant
   */
  const hasPermission = useCallback(
    (permission: string): boolean => {
      if (!currentTenant?.permissions) return false;
      return currentTenant.permissions.includes(permission);
    },
    [currentTenant]
  );

  /**
   * Check if user has a specific role in current tenant
   */
  const hasRole = useCallback(
    (role: string): boolean => {
      if (!currentTenant?.role) return false;
      return currentTenant.role === role;
    },
    [currentTenant]
  );

  const value = useMemo<TenantContextState>(
    () => ({
      currentTenant,
      availableTenants,
      isLoading,
      error,
      switchTenant,
      refreshTenants,
      hasPermission,
      hasRole,
    }),
    [
      currentTenant,
      availableTenants,
      isLoading,
      error,
      switchTenant,
      refreshTenants,
      hasPermission,
      hasRole,
    ]
  );

  return (
    <TenantContext.Provider value={value}>{children}</TenantContext.Provider>
  );
}

/**
 * Hook to access tenant context
 *
 * @throws Error if used outside TenantProvider
 */
export function useTenant(): TenantContextState {
  const context = useContext(TenantContext);

  if (!context) {
    throw new Error("useTenant must be used within a TenantProvider");
  }

  return context;
}

/**
 * Hook to get just the current tenant (for simple use cases)
 */
export function useCurrentTenant(): Tenant | null {
  const { currentTenant } = useTenant();
  return currentTenant;
}

/**
 * Hook to check if tenant is loading
 */
export function useTenantLoading(): boolean {
  const { isLoading } = useTenant();
  return isLoading;
}

/**
 * HOC to require tenant selection
 */
export function withTenant<P extends object>(
  Component: React.ComponentType<P & { tenant: Tenant }>
): React.FC<P> {
  return function WithTenantWrapper(props: P) {
    const { currentTenant, isLoading } = useTenant();

    if (isLoading) {
      return (
        <div className="flex items-center justify-center p-8">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600" />
        </div>
      );
    }

    if (!currentTenant) {
      return (
        <div className="flex items-center justify-center p-8">
          <p className="text-gray-500">Please select a tenant to continue.</p>
        </div>
      );
    }

    return <Component {...props} tenant={currentTenant} />;
  };
}
