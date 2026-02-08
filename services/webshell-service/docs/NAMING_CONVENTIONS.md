# Naming Conventions - WebShell Service

This document outlines the naming conventions used in this Next.js/React/TypeScript project.
Based on industry best practices from Google TypeScript Style Guide, React TypeScript Cheatsheets, and Next.js conventions.

## Why `lib/` (not `libs/`)?

**We use `lib/` (singular)** for these reasons:
- **Next.js convention**: Official Next.js examples and documentation use `lib/`
- **Semantic meaning**: "lib" is short for "library" (a collection), not "libraries"
- **Industry standard**: Most React/Next.js projects use `lib/`
- **Consistency**: shadcn/ui and other popular libraries use `lib/`

## Enforcement

Naming conventions are enforced automatically via:

### ESLint Rules

1. **File Naming** - `eslint-plugin-check-file`
   - Enforces kebab-case for all `.ts` and `.tsx` files
   - Enforces kebab-case for folder names in `src/` and `tests/`
   - Run `npm run lint` to check

2. **Code Naming** - `@typescript-eslint/naming-convention`
   - Interfaces/Types: PascalCase (no `I` prefix)
   - Enums: PascalCase, members: UPPER_CASE
   - Variables/Functions: camelCase (PascalCase for React components)

See `eslint.config.mjs` for full configuration.

### Other Measures
- **GitHub Copilot instructions** - `.github/instructions/webshell-naming-conventions.instructions.md`
- **PR reviews** - Team reviews should check naming
- **This documentation** - Reference for developers

## File Naming Conventions

### Component Files
- **Format**: `kebab-case.tsx`
- **Examples**:
  - `button.tsx`
  - `dropdown-menu.tsx`
  - `audit-log-table.tsx`
  - `auth-provider.tsx`
- **Note**: Inside the file, the component itself uses PascalCase (e.g., `export function AuditLogTable() {}`)

### Hook Files
- **Format**: `use-hook-name.ts` (kebab-case with `use-` prefix)
- **Examples**:
  - `use-auth.ts`
  - `use-mobile.ts`
  - `use-api-query.ts`
  - `use-debounce.ts`
- **Note**: Inside the file, the hook function uses camelCase (e.g., `export function useAuth() {}`)

### Utility/Service Files
- **Format**: `kebab-case.ts`
- **Examples**:
  - `api-client.ts`
  - `error-handling.ts`
  - `utils.ts`

### Type Files
- **Format**: `kebab-case.ts`
- **Examples**:
  - `audit.ts`
  - `auth.ts`

### Configuration Files
- **Format**: `kebab-case.ts` or framework defaults
- **Examples**:
  - `constants.ts`
  - `env.ts`

## Directory Structure

### Standard Directories
- `lib/` - Utility functions, API clients, auth configuration (singular, per Next.js convention)
- `hooks/` - Custom React hooks
- `components/` - React components organized by feature/domain
- `types/` - TypeScript type definitions
- `services/` - API service functions
- `contexts/` - React context providers
- `config/` - Application configuration
- `features/` - Feature-based code organization

### Directory Naming
- **Format**: `kebab-case`
- **Examples**:
  - `components/audit/`
  - `components/ui/`
  - `app/(dashboard)/`

## Code Naming Conventions

### Variables
- **Format**: `camelCase`
- **Examples**:
  - `const userName = "John";`
  - `let isLoading = false;`

### Constants (true constants)
- **Format**: `CONSTANT_CASE` for values that should never be modified
- **Examples**:
  - `const MAX_RETRIES = 3;`
  - `const DEFAULT_PAGE_SIZE = 20;`

### Functions
- **Format**: `camelCase`
- **Examples**:
  - `function getUserById() {}`
  - `const handleSubmit = () => {};`

### React Components
- **Format**: `PascalCase`
- **Examples**:
  - `function AuditLogTable() {}`
  - `const UserProfile: React.FC = () => {};`

### React Hooks
- **Format**: `camelCase` starting with `use`
- **Examples**:
  - `function useAuth() {}`
  - `function useAuditEvents() {}`

### Interfaces and Types
- **Format**: `PascalCase` (without "I" prefix)
- **Examples**:
  - `interface User {}`
  - `type AuditEvent = {}`
  - `interface ApiResponse<T> {}`

### Enums
- **Format**: `PascalCase` for name, `CONSTANT_CASE` for values
- **Examples**:
  ```typescript
  enum AuditAction {
    CREATE = "CREATE",
    UPDATE = "UPDATE",
    DELETE = "DELETE",
  }
  ```

### Type Parameters (Generics)
- **Format**: Single uppercase letter or descriptive PascalCase
- **Examples**:
  - `<T>`, `<K, V>`
  - `<TData>`, `<TResponse>`

## Import/Export Conventions

### Barrel Exports
- Each major directory should have an `index.ts` for barrel exports
- Example:
  ```typescript
  // hooks/index.ts
  export { useAuth } from './use-auth';
  export { useApiQuery } from './use-api-query';
  ```

### Import Order
1. External packages (react, next, etc.)
2. Internal absolute imports (@/components, @/hooks)
3. Relative imports (./utils, ../types)
4. Type-only imports

### Path Aliases
- Use `@/` for src-relative imports
- Example: `import { Button } from "@/components/ui/button";`

## Best Practices

### Do
- ✅ Use descriptive names that explain the purpose
- ✅ Keep file names lowercase with hyphens for consistency
- ✅ Use barrel exports to simplify imports
- ✅ Keep component/hook names matching their functionality

### Don't
- ❌ Use abbreviations that aren't widely understood
- ❌ Mix naming conventions (e.g., some hooks as `useX.ts` and others as `use-x.ts`)
- ❌ Use the `I` prefix for interfaces (outdated practice)
- ❌ Use `class` for TypeScript-only types (use `interface` or `type`)

## Project Structure Example

```
src/
├── app/                    # Next.js App Router
│   ├── (dashboard)/       # Route groups
│   ├── api/               # API routes
│   └── layout.tsx
├── components/
│   ├── audit/
│   │   ├── audit-log-table.tsx
│   │   ├── audit-filters.tsx
│   │   └── index.ts
│   ├── ui/
│   │   ├── button.tsx
│   │   └── dropdown-menu.tsx
│   └── providers/
│       └── auth-provider.tsx
├── hooks/
│   ├── use-auth.ts
│   ├── use-api-query.ts
│   └── index.ts
├── lib/
│   ├── api-client.ts
│   ├── auth.ts
│   ├── utils.ts
│   └── index.ts
├── types/
│   └── audit.ts
└── services/
    └── audit-api.ts
```
