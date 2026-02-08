# Frontend Architecture - WebShell Service

> **Status:** Implementation In Progress  
> **Last Updated:** 2026-02-01  
> **Related ADRs:** [ADR-001](adr/0001-clean-architecture.md), [ADR-003](adr/0003-observability-stack.md)

## Overview

Enterprise-grade Next.js 15 + React 19 frontend with OAuth 2.0/OIDC authentication, multi-tenant support, and comprehensive testing infrastructure. Follows Clean Architecture principles adapted for frontend development.

## Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Framework | Next.js (App Router) | 15.4.6 |
| UI Library | React | 19.1.0 |
| Styling | Tailwind CSS + shadcn/ui | v4 |
| State Management | React Query + Context | v5 |
| Authentication | NextAuth.js (OIDC) | v5 beta |
| Form Handling | React Hook Form + Zod | latest |
| Testing | Vitest + Playwright | latest |
| Build Tool | Turbopack (dev) | built-in |

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                        Presentation Layer                        │
│  src/app/                                                        │
│  ├── (public)/          Public routes (landing, about)          │
│  ├── (auth)/            Auth flow (login, logout, error)        │
│  └── (dashboard)/       Protected routes (requires auth)        │
├─────────────────────────────────────────────────────────────────┤
│                         Feature Layer                            │
│  src/features/                                                   │
│  ├── auth/              Authentication module                   │
│  ├── audit/             Audit dashboard                         │
│  ├── tenants/           Tenant management                       │
│  └── admin/             Admin panel (RBAC protected)            │
├─────────────────────────────────────────────────────────────────┤
│                       Infrastructure Layer                       │
│  src/libs/              Core utilities                          │
│  ├── auth.ts            NextAuth.js configuration               │
│  ├── api-client.ts      HTTP client with auth + tracing         │
│  └── logger.ts          Structured JSON logging                 │
├─────────────────────────────────────────────────────────────────┤
│                         Shared Layer                             │
│  src/components/        Reusable UI components (shadcn/ui)      │
│  src/hooks/             Global React hooks                      │
│  src/types/             TypeScript type definitions             │
│  src/contexts/          React Context providers                 │
└─────────────────────────────────────────────────────────────────┘
```

## Directory Structure

```
services/webshell-service/src/
├── app/                          # Next.js App Router
│   ├── (public)/                 # Unauthenticated routes
│   │   ├── page.tsx              # Landing page
│   │   └── about/page.tsx
│   ├── (auth)/                   # Auth flow routes
│   │   ├── login/page.tsx
│   │   ├── logout/page.tsx
│   │   └── error/page.tsx
│   ├── (dashboard)/              # Protected routes
│   │   ├── layout.tsx            # Auth-required layout
│   │   ├── page.tsx              # Dashboard home
│   │   ├── audit/                # Audit feature pages
│   │   ├── settings/             # User/tenant settings
│   │   └── admin/                # Admin panel
│   ├── api/auth/[...nextauth]/   # NextAuth API route
│   ├── layout.tsx                # Root layout
│   └── globals.css               # Global styles
│
├── components/
│   ├── ui/                       # shadcn/ui components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── data-table.tsx
│   │   └── ...
│   ├── layout/
│   │   ├── header.tsx
│   │   ├── sidebar.tsx
│   │   └── footer.tsx
│   └── providers/
│       ├── auth-provider.tsx
│       ├── query-provider.tsx
│       └── theme-provider.tsx
│
├── features/                     # Domain-driven features
│   ├── auth/
│   │   ├── components/
│   │   │   ├── login-form.tsx
│   │   │   ├── user-menu.tsx
│   │   │   └── auth-guard.tsx
│   │   ├── hooks/
│   │   │   └── use-auth.ts
│   │   ├── services/
│   │   │   └── auth-service.ts
│   │   └── types.ts
│   ├── audit/
│   │   ├── components/
│   │   │   ├── audit-table.tsx
│   │   │   ├── audit-filters.tsx
│   │   │   └── audit-detail.tsx
│   │   ├── hooks/
│   │   │   └── use-audit-events.ts
│   │   ├── services/
│   │   │   └── audit-service.ts
│   │   └── types.ts
│   ├── tenants/
│   │   ├── components/
│   │   │   ├── tenant-switcher.tsx
│   │   │   ├── tenant-settings.tsx
│   │   │   └── tenant-members.tsx
│   │   ├── hooks/
│   │   │   └── use-tenants.ts
│   │   ├── services/
│   │   │   └── tenant-service.ts
│   │   └── types.ts
│   └── admin/
│       ├── components/
│       ├── hooks/
│       ├── services/
│       └── types.ts
│
├── contexts/
│   └── TenantContext.tsx         # Multi-tenant context
│
├── libs/
│   ├── auth.ts                   # NextAuth configuration
│   ├── api-client.ts             # HTTP client wrapper
│   ├── logger.ts                 # Structured logging
│   ├── constants.ts              # App constants
│   └── utils.ts                  # General utilities
│
├── hooks/
│   ├── use-debounce.ts
│   ├── use-correlation-id.ts
│   └── use-toast.ts
│
├── types/
│   ├── api.ts                    # API response types
│   ├── user.ts                   # User/auth types
│   ├── tenant.ts                 # Tenant types
│   ├── audit.ts                  # Audit domain types
│   └── next-auth.d.ts            # NextAuth type extensions
│
└── config/
    └── env.ts                    # Environment configuration
```

## Authentication Flow

```
┌──────────┐     ┌──────────────┐     ┌──────────────────┐
│  User    │────▶│  WebShell    │────▶│ Identity Service │
│ Browser  │     │  Frontend    │     │   (OAuth2/OIDC)  │
└──────────┘     └──────────────┘     └──────────────────┘
     │                  │                      │
     │ 1. Click Login   │                      │
     │─────────────────▶│                      │
     │                  │ 2. Initiate OIDC     │
     │                  │    (PKCE S256)       │
     │                  │─────────────────────▶│
     │                  │                      │
     │ 3. Redirect to   │◀─────────────────────│
     │    /oauth2/authorize                    │
     │◀─────────────────│                      │
     │                  │                      │
     │ 4. User authenticates                   │
     │────────────────────────────────────────▶│
     │                  │                      │
     │ 5. Auth code     │                      │
     │◀────────────────────────────────────────│
     │                  │                      │
     │ 6. Callback      │                      │
     │─────────────────▶│                      │
     │                  │ 7. Exchange code     │
     │                  │    for tokens        │
     │                  │─────────────────────▶│
     │                  │                      │
     │                  │ 8. Access + Refresh  │
     │                  │    + ID tokens       │
     │                  │◀─────────────────────│
     │                  │                      │
     │ 9. Session       │                      │
     │    cookie set    │                      │
     │◀─────────────────│                      │
```

### NextAuth.js Configuration

```typescript
// src/libs/auth.ts
export const authConfig: NextAuthConfig = {
  providers: [
    {
      id: "identity-service",
      name: "Identity Service",
      type: "oidc",
      issuer: process.env.IDENTITY_SERVICE_URL,
      clientId: process.env.OAUTH_CLIENT_ID,
      clientSecret: "", // Empty for public clients
      authorization: {
        params: {
          scope: "openid profile email offline_access",
        },
      },
    },
  ],
  callbacks: {
    async jwt({ token, account }) {
      // Store tokens, handle refresh
    },
    async session({ session, token }) {
      // Expose accessToken to client
    },
  },
};
```

## Multi-Tenancy Architecture

### Tenant Context

```typescript
// src/contexts/TenantContext.tsx
interface TenantContextValue {
  currentTenant: Tenant | null;
  tenants: Tenant[];           // All user's tenants
  isLoading: boolean;
  switchTenant: (tenantId: string) => Promise<void>;
  createTenant: (data: CreateTenantInput) => Promise<Tenant>;
}
```

### Tenant Resolution Flow

1. **JWT Token** contains `tid` (tenant ID) claim
2. **TenantContext** extracts tenant from session
3. **API Client** injects `X-Tenant-ID` header on all requests
4. **Backend** validates tenant access and scopes data

### Tenant Switching UI

- Dropdown in header showing current tenant
- List all user's tenants with role badges
- "Create New Tenant" option
- Persist selection to localStorage

## API Client

### Request Flow

```typescript
// src/libs/api-client.ts
export async function apiClient<T>(endpoint: string, options?: RequestOptions): Promise<T> {
  const session = await auth();
  const correlationId = generateCorrelationId();
  
  const headers = {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${session?.accessToken}`,
    "X-Tenant-ID": getCurrentTenantId(),
    "X-Correlation-ID": correlationId,
    "X-Request-ID": generateRequestId(),
  };
  
  const response = await fetch(`${API_URL}${endpoint}`, { ...options, headers });
  
  if (!response.ok) {
    throw new APIError(response.status, await response.json());
  }
  
  return response.json();
}
```

### Error Handling

Maps backend exceptions to frontend error types:

| HTTP Status | Backend Exception | Frontend Handling |
|-------------|------------------|-------------------|
| 401 | UnauthorizedException | Redirect to login |
| 403 | ForbiddenException | Show access denied |
| 404 | NotFoundException | Show not found page |
| 422 | ValidationException | Display form errors |
| 429 | RateLimitException | Show retry message |
| 500+ | InternalServerException | Show error toast |

## Observability

### Correlation ID Propagation

All requests include:
- `X-Correlation-ID`: Traces request across services
- `X-Request-ID`: Unique per-request identifier

### Structured Logging

```typescript
// src/libs/logger.ts
export const logger = {
  info: (message: string, context?: Record<string, unknown>) => {
    console.log(JSON.stringify({
      timestamp: new Date().toISOString(),
      level: "info",
      service: "webshell",
      message,
      correlationId: getCurrentCorrelationId(),
      tenantId: getCurrentTenantId(),
      ...context,
    }));
  },
};
```

## Testing Strategy

### Test Pyramid

```
         ┌───────────┐
         │    E2E    │  Playwright (critical flows)
         │   Tests   │
        ┌┴───────────┴┐
        │ Integration │  React Testing Library + MSW
        │   Tests     │
       ┌┴─────────────┴┐
       │   Unit Tests  │  Vitest (hooks, utils, services)
       └───────────────┘
```

### Test Structure

```
tests/
├── setup.ts                    # Test configuration
├── fixtures/                   # Shared test data
│   ├── auth.ts
│   ├── audit.ts
│   └── tenant.ts
├── unit/
│   ├── hooks/
│   ├── libs/
│   └── features/
├── integration/
│   └── pages/
└── e2e/
    ├── auth.spec.ts
    ├── audit.spec.ts
    └── tenant.spec.ts
```

## CI/CD Pipeline

### GitHub Actions Workflow

```yaml
# .github/workflows/webshell-ci.yml
jobs:
  lint-typecheck:     # ESLint + TypeScript
  unit-tests:         # Vitest with coverage
  e2e-tests:          # Playwright
  build-image:        # Docker build + push to GHCR
```

### Quality Gates

- [ ] ESLint passes (zero errors)
- [ ] TypeScript compiles (strict mode)
- [ ] Unit test coverage ≥ 80%
- [ ] E2E critical paths pass
- [ ] Docker image builds successfully

## Security Considerations

### Authentication
- PKCE (S256) required for OAuth flow
- Tokens stored in HTTP-only secure cookies
- Automatic token refresh before expiry

### Authorization
- Route-level auth guards via middleware
- Component-level RBAC checks
- API responses filtered by tenant

### Data Protection
- No sensitive data in localStorage
- Environment variables validated at startup
- CSP headers configured in Next.js

## Environment Variables

```env
# Identity Service
IDENTITY_SERVICE_URL=http://localhost:8003
OAUTH_CLIENT_ID=webshell-frontend
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=<generated-secret>

# API Gateway
NEXT_PUBLIC_API_URL=http://localhost:8000

# Multi-Tenancy
NEXT_PUBLIC_DEFAULT_TENANT_ID=default

# Feature Flags
NEXT_PUBLIC_FEATURE_FLAGS_ENABLED=true

# Observability
NEXT_PUBLIC_LOG_LEVEL=info
```

## Related Documentation

- [Integration Guide](integration-guide.md)
- [ADR-001: Clean Architecture](adr/0001-clean-architecture.md)
- [ADR-003: Observability Stack](adr/0003-observability-stack.md)
- [Identity Service README](../services/identity-service/README.md)
- [Audit Service README](../services/audit-service/README.md)
