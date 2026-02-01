---
applyTo: 'services/webshell-service/**/*'
description: 'Naming conventions for the WebShell Next.js/React/TypeScript frontend service'
---

# WebShell Service Naming Conventions

**Enforced by ESLint** via `eslint-plugin-check-file` and `@typescript-eslint/naming-convention`.

## CRITICAL: File Naming Rules

When creating or modifying files in the webshell-service, you MUST follow these naming conventions:

### Component Files
- **Format**: `kebab-case.tsx`
- **Examples**: `button.tsx`, `audit-log-table.tsx`, `tenant-switcher.tsx`
- **WRONG**: `Button.tsx`, `AuditLogTable.tsx`, `TenantSwitcher.tsx`

### Hook Files
- **Format**: `use-hook-name.ts` (kebab-case with `use-` prefix)
- **Examples**: `use-auth.ts`, `use-api-query.ts`, `use-debounce.ts`
- **WRONG**: `useAuth.ts`, `useApiQuery.ts`

### Context Files
- **Format**: `kebab-case.tsx`
- **Examples**: `tenant-context.tsx`, `auth-context.tsx`
- **WRONG**: `TenantContext.tsx`, `AuthContext.tsx`

### Test Files
- **Format**: `kebab-case.test.tsx` or `kebab-case.test.ts`
- **Examples**: `use-tenant.test.tsx`, `audit-components.test.tsx`
- **WRONG**: `useTenant.test.tsx`, `AuditComponents.test.tsx`

### Utility/Service Files
- **Format**: `kebab-case.ts`
- **Examples**: `api-client.ts`, `error-handling.ts`

### Type Files
- **Format**: `kebab-case.ts`
- **Examples**: `audit.ts`, `auth-types.ts`

## Directory Structure

Use `lib/` (singular) NOT `libs/` for utility functions and libraries.

Standard directories:
- `lib/` - Utility functions, API clients (NOT libs/)
- `hooks/` - Custom React hooks
- `components/` - React components
- `contexts/` - React context providers
- `types/` - TypeScript type definitions
- `services/` - API service functions

## Code Naming (Inside Files)

While file names use kebab-case, code inside uses standard conventions:

```typescript
// File: components/audit/audit-log-table.tsx
export function AuditLogTable() { ... }  // PascalCase component

// File: hooks/use-auth.ts
export function useAuth() { ... }  // camelCase hook

// File: types/audit.ts
export interface AuditEvent { ... }  // PascalCase interface
export enum AuditAction { CREATE = "CREATE" }  // PascalCase enum, UPPER_CASE values
```

## Barrel Exports

Always use barrel exports (index.ts) and update them when adding new files:

```typescript
// hooks/index.ts
export { useAuth } from './use-auth';
export { useApiQuery } from './use-api-query';
```

## Import Conventions

- Use `@/` path alias for src-relative imports
- Prefer importing from barrel exports when available

```typescript
// Good
import { useAuth } from "@/hooks";
import { AuditLogTable } from "@/components/audit";

// Also acceptable for specific imports
import { useAuth } from "@/hooks/use-auth";
```

## Checklist Before Creating Files

- [ ] File name is kebab-case (lowercase with hyphens)
- [ ] Hook files start with `use-`
- [ ] Test files end with `.test.tsx` or `.test.ts`
- [ ] Using `lib/` not `libs/`
- [ ] Barrel export (index.ts) is updated
