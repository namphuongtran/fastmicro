/**
 * Tenants Page
 *
 * Read-only page displaying current tenant information and available tenants.
 * Users can view their tenant memberships and switch between tenants.
 */
"use client";

import { Building2, Users, Shield, CheckCircle, Clock } from "lucide-react";

import { useTenant } from "@/contexts/tenant-context";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

// ============================================================================
// Helper Components
// ============================================================================

function TenantCardSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-32" />
      </CardHeader>
      <CardContent className="space-y-4">
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </CardContent>
    </Card>
  );
}

function RoleBadge({ role }: { role: string }) {
  const variants: Record<string, "default" | "secondary" | "outline"> = {
    admin: "default",
    owner: "default",
    member: "secondary",
    viewer: "outline",
  };

  return (
    <Badge variant={variants[role.toLowerCase()] || "secondary"}>
      {role}
    </Badge>
  );
}

// ============================================================================
// Page Component
// ============================================================================

export default function TenantsPage() {
  const {
    currentTenant,
    availableTenants,
    isLoading,
    error,
    switchTenant,
    hasRole,
  } = useTenant();

  // Loading state
  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Tenants</h1>
          <p className="text-muted-foreground">
            Loading tenant information...
          </p>
        </div>
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          <TenantCardSkeleton />
          <TenantCardSkeleton />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Tenants</h1>
          <p className="text-muted-foreground text-red-600">
            Error loading tenants: {error}
          </p>
        </div>
      </div>
    );
  }

  const isAdmin = hasRole("admin") || hasRole("owner");

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Tenants</h1>
        <p className="text-muted-foreground">
          View and manage your tenant memberships
        </p>
      </div>

      {/* Current Tenant Card */}
      {currentTenant && (
        <Card className="border-primary/50 bg-primary/5">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary text-primary-foreground">
                  <Building2 className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="flex items-center gap-2">
                    {currentTenant.name}
                    <CheckCircle className="h-4 w-4 text-green-600" />
                  </CardTitle>
                  <CardDescription>Current Tenant</CardDescription>
                </div>
              </div>
              {currentTenant.role && <RoleBadge role={currentTenant.role} />}
            </div>
          </CardHeader>
          <CardContent>
            <dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-1">
                <dt className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                  <Shield className="h-3.5 w-3.5" />
                  Tenant ID
                </dt>
                <dd className="font-mono text-sm">{currentTenant.id}</dd>
              </div>
              {currentTenant.slug && (
                <div className="space-y-1">
                  <dt className="text-sm font-medium text-muted-foreground">
                    Slug
                  </dt>
                  <dd className="font-mono text-sm">{currentTenant.slug}</dd>
                </div>
              )}
              <div className="space-y-1">
                <dt className="text-sm font-medium text-muted-foreground flex items-center gap-1">
                  <Users className="h-3.5 w-3.5" />
                  Your Role
                </dt>
                <dd className="text-sm capitalize">
                  {currentTenant.role || "Member"}
                </dd>
              </div>
              {currentTenant.permissions && currentTenant.permissions.length > 0 && (
                <div className="space-y-1">
                  <dt className="text-sm font-medium text-muted-foreground">
                    Permissions
                  </dt>
                  <dd className="flex flex-wrap gap-1">
                    {currentTenant.permissions.slice(0, 3).map((perm) => (
                      <Badge key={perm} variant="outline" className="text-xs">
                        {perm}
                      </Badge>
                    ))}
                    {currentTenant.permissions.length > 3 && (
                      <Badge variant="outline" className="text-xs">
                        +{currentTenant.permissions.length - 3} more
                      </Badge>
                    )}
                  </dd>
                </div>
              )}
            </dl>

            {isAdmin && (
              <div className="mt-4 pt-4 border-t">
                <p className="text-sm text-muted-foreground">
                  <Shield className="h-3.5 w-3.5 inline mr-1" />
                  As an admin, you can manage this tenant via the Admin API.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Available Tenants */}
      {availableTenants.length > 1 && (
        <div className="space-y-4">
          <h2 className="text-lg font-semibold">All Tenants</h2>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {availableTenants.map((tenant) => {
              const isCurrent = tenant.id === currentTenant?.id;
              return (
                <Card
                  key={tenant.id}
                  className={`cursor-pointer transition-colors hover:border-primary/50 ${
                    isCurrent ? "border-primary bg-primary/5" : ""
                  }`}
                  onClick={() => !isCurrent && switchTenant(tenant.id)}
                >
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-base flex items-center gap-2">
                        <div className="flex h-8 w-8 items-center justify-center rounded-md bg-muted">
                          {tenant.name.charAt(0).toUpperCase()}
                        </div>
                        {tenant.name}
                      </CardTitle>
                      {isCurrent && (
                        <Badge variant="default" className="text-xs">
                          Current
                        </Badge>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">Role</span>
                      <span className="capitalize">{tenant.role || "Member"}</span>
                    </div>
                    {!isCurrent && (
                      <p className="mt-2 text-xs text-muted-foreground">
                        Click to switch to this tenant
                      </p>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* Single Tenant Info */}
      {availableTenants.length === 1 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Clock className="h-4 w-4" />
              Single Tenant
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              You are a member of one tenant. Contact your administrator if you
              need access to additional tenants.
            </p>
          </CardContent>
        </Card>
      )}

      {/* No Tenants */}
      {availableTenants.length === 0 && !currentTenant && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">No Tenants</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              You are not a member of any tenant. Please contact your
              administrator to be added to a tenant.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
