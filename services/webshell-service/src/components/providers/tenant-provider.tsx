"use client";

import { TenantProvider as BaseTenantProvider } from "@/contexts/tenant-context";
import { clientEnv } from "@/config/env";

/**
 * Tenant Provider Wrapper
 *
 * Wraps the TenantProvider with application-specific configuration.
 * This provider should be placed inside AuthProvider but can wrap
 * the rest of the application.
 */

interface TenantProviderWrapperProps {
  children: React.ReactNode;
}

export function TenantProviderWrapper({ children }: TenantProviderWrapperProps) {
  return (
    <BaseTenantProvider defaultTenantId={clientEnv.NEXT_PUBLIC_DEFAULT_TENANT_ID}>
      {children}
    </BaseTenantProvider>
  );
}
