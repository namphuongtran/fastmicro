/**
 * Custom test utilities extending Testing Library
 * Provides pre-configured render with all necessary providers
 */
import React, { ReactElement, ReactNode } from 'react';
import { render, RenderOptions, RenderResult } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// Create a test-specific QueryClient with sensible defaults
function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false, // Don't retry failed queries in tests
        gcTime: 0, // Don't cache queries between tests
        staleTime: 0, // Always consider data stale
      },
      mutations: {
        retry: false,
      },
    },
  });
}

// All providers wrapper component
interface AllProvidersProps {
  children: ReactNode;
  queryClient?: QueryClient;
}

function AllProviders({ children, queryClient }: AllProvidersProps): ReactElement {
  const client = queryClient || createTestQueryClient();

  return (
    <QueryClientProvider client={client}>
      {children}
    </QueryClientProvider>
  );
}

// Custom render options
interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  queryClient?: QueryClient;
}

// Custom render function that wraps components with all providers
function customRender(ui: ReactElement, options: CustomRenderOptions = {}): RenderResult {
  const { queryClient, ...renderOptions } = options;

  return render(ui, {
    wrapper: ({ children }) => <AllProviders queryClient={queryClient}>{children}</AllProviders>,
    ...renderOptions,
  });
}

// Setup userEvent with pre-configured options
function setupUser() {
  return userEvent.setup();
}

// Re-export everything from testing library
export * from '@testing-library/react';

// Override render with our custom version
export { customRender as render, setupUser, createTestQueryClient };

// Utility to wait for loading states to resolve
export async function waitForLoadingToFinish(): Promise<void> {
  // Wait for any loading indicators to disappear
  await new Promise((resolve) => setTimeout(resolve, 0));
}

// Utility to mock fetch response
export function mockFetchResponse<T>(data: T, status = 200): void {
  global.fetch = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(data),
    text: () => Promise.resolve(JSON.stringify(data)),
  });
}

// Utility to mock fetch error
export function mockFetchError(message: string, status = 500): void {
  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status,
    json: () => Promise.resolve({ error: message }),
    text: () => Promise.resolve(JSON.stringify({ error: message })),
  });
}
