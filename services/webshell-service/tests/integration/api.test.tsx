/**
 * API Client integration tests
 * Tests the API client with MSW mocked responses
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query';

// Test component that uses the API
function TestApiComponent({ endpoint }: { endpoint: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['test', endpoint],
    queryFn: async () => {
      const response = await fetch(`http://localhost:8000${endpoint}`);
      if (!response.ok) {
        throw new Error('API error');
      }
      return response.json();
    },
  });

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {(error as Error).message}</div>;
  return <div data-testid="api-result">{JSON.stringify(data)}</div>;
}

describe('API Integration', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
  });

  it('should fetch health check successfully', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <TestApiComponent endpoint="/health" />
      </QueryClientProvider>
    );

    expect(screen.getByText('Loading...')).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByTestId('api-result')).toBeInTheDocument();
    });

    expect(screen.getByTestId('api-result')).toHaveTextContent('healthy');
  });

  it('should fetch users successfully', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <TestApiComponent endpoint="/api/v1/users" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('api-result')).toBeInTheDocument();
    });

    expect(screen.getByTestId('api-result')).toHaveTextContent('items');
  });

  it('should fetch tenants successfully', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <TestApiComponent endpoint="/api/v1/tenants" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('api-result')).toBeInTheDocument();
    });

    expect(screen.getByTestId('api-result')).toHaveTextContent('Test Tenant');
  });

  it('should fetch audit logs successfully', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <TestApiComponent endpoint="/api/v1/audit/logs" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByTestId('api-result')).toBeInTheDocument();
    });

    expect(screen.getByTestId('api-result')).toHaveTextContent('user.login');
  });

  it('should handle API errors gracefully', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <TestApiComponent endpoint="/api/v1/error-test" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Error:/)).toBeInTheDocument();
    });
  });

  it('should handle unauthorized responses', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <TestApiComponent endpoint="/api/v1/unauthorized" />
      </QueryClientProvider>
    );

    await waitFor(() => {
      expect(screen.getByText(/Error:/)).toBeInTheDocument();
    });
  });
});
