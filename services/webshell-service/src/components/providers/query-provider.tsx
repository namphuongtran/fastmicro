/**
 * React Query provider for data fetching.
 *
 * Configures TanStack Query with sensible defaults
 * for the enterprise application.
 *
 * @module components/providers/query-provider
 */

"use client";

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

// Dynamic import for devtools to avoid SSR issues
const ReactQueryDevtools =
  process.env.NODE_ENV === "development"
    ? // eslint-disable-next-line @typescript-eslint/no-require-imports
      require("@tanstack/react-query-devtools").ReactQueryDevtools
    : () => null;

interface QueryProviderProps {
  /** Child components */
  children: React.ReactNode;
}

/**
 * Create a new QueryClient with default options.
 */
function makeQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Data is fresh for 60 seconds
        staleTime: 60 * 1000,
        // Keep unused data in cache for 5 minutes
        gcTime: 5 * 60 * 1000,
        // Retry failed requests once
        retry: 1,
        // Don't refetch on mount if data is fresh
        refetchOnMount: false,
        // Refetch on window focus in production
        refetchOnWindowFocus: process.env.NODE_ENV === "production",
      },
      mutations: {
        // Retry failed mutations once
        retry: 1,
      },
    },
  });
}

// Browser-side QueryClient singleton
let browserQueryClient: QueryClient | undefined = undefined;

/**
 * Get or create QueryClient.
 * Creates a new client on server, reuses singleton on browser.
 */
function getQueryClient() {
  if (typeof window === "undefined") {
    // Server: always make a new query client
    return makeQueryClient();
  } else {
    // Browser: make a new query client if we don't already have one
    if (!browserQueryClient) {
      browserQueryClient = makeQueryClient();
    }
    return browserQueryClient;
  }
}

/**
 * React Query provider component.
 *
 * Provides the QueryClient to the application for data fetching.
 * Includes React Query DevTools in development.
 *
 * @example
 * ```tsx
 * // In app/layout.tsx
 * export default function RootLayout({ children }) {
 *   return (
 *     <html>
 *       <body>
 *         <QueryProvider>
 *           {children}
 *         </QueryProvider>
 *       </body>
 *     </html>
 *   );
 * }
 * ```
 */
export function QueryProvider({ children }: QueryProviderProps) {
  // Use useState to ensure a new QueryClient is not created on every render
  const [queryClient] = useState(() => getQueryClient());

  return (
    <QueryClientProvider client={queryClient}>
      {children}
      {process.env.NODE_ENV === "development" && (
        <ReactQueryDevtools initialIsOpen={false} />
      )}
    </QueryClientProvider>
  );
}
