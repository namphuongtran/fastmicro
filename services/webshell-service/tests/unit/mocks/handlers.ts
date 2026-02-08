/**
 * MSW request handlers for API mocking
 * Defines mock responses for all API endpoints used in tests
 */
import { http, HttpResponse } from 'msw';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Mock data
export const mockUser = {
  id: 'user-123',
  email: 'test@example.com',
  name: 'Test User',
  tenantId: 'tenant-123',
  roles: ['user'],
  createdAt: new Date().toISOString(),
  updatedAt: new Date().toISOString(),
};

export const mockTenants = [
  {
    id: 'tenant-123',
    name: 'Test Tenant',
    slug: 'test-tenant',
    status: 'active',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'tenant-456',
    name: 'Another Tenant',
    slug: 'another-tenant',
    status: 'active',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
];

export const mockAuditLogs = [
  {
    id: 'audit-1',
    action: 'user.login',
    actorId: 'user-123',
    actorEmail: 'test@example.com',
    resourceType: 'session',
    resourceId: 'session-abc',
    tenantId: 'tenant-123',
    ipAddress: '192.168.1.1',
    userAgent: 'Mozilla/5.0',
    timestamp: new Date().toISOString(),
    metadata: {},
  },
  {
    id: 'audit-2',
    action: 'user.logout',
    actorId: 'user-123',
    actorEmail: 'test@example.com',
    resourceType: 'session',
    resourceId: 'session-abc',
    tenantId: 'tenant-123',
    ipAddress: '192.168.1.1',
    userAgent: 'Mozilla/5.0',
    timestamp: new Date().toISOString(),
    metadata: {},
  },
];

// API handlers
export const handlers = [
  // Health check
  http.get(`${API_BASE_URL}/health`, () => {
    return HttpResponse.json({ status: 'healthy' });
  }),

  // User endpoints
  http.get(`${API_BASE_URL}/api/v1/users/me`, () => {
    return HttpResponse.json(mockUser);
  }),

  http.get(`${API_BASE_URL}/api/v1/users`, ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const limit = parseInt(url.searchParams.get('limit') || '10');

    return HttpResponse.json({
      items: [mockUser],
      total: 1,
      page,
      limit,
      totalPages: 1,
    });
  }),

  // Tenant endpoints
  http.get(`${API_BASE_URL}/api/v1/tenants`, () => {
    return HttpResponse.json({
      items: mockTenants,
      total: mockTenants.length,
      page: 1,
      limit: 10,
      totalPages: 1,
    });
  }),

  http.get(`${API_BASE_URL}/api/v1/tenants/:id`, ({ params }) => {
    const tenant = mockTenants.find((t) => t.id === params.id);
    if (!tenant) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(tenant);
  }),

  http.post(`${API_BASE_URL}/api/v1/tenants`, async ({ request }) => {
    const body = (await request.json()) as Record<string, unknown>;
    const newTenant = {
      id: `tenant-${Date.now()}`,
      ...body,
      status: 'active',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    return HttpResponse.json(newTenant, { status: 201 });
  }),

  // Audit endpoints
  http.get(`${API_BASE_URL}/api/v1/audit/logs`, ({ request }) => {
    const url = new URL(request.url);
    const page = parseInt(url.searchParams.get('page') || '1');
    const limit = parseInt(url.searchParams.get('limit') || '10');

    return HttpResponse.json({
      items: mockAuditLogs,
      total: mockAuditLogs.length,
      page,
      limit,
      totalPages: 1,
    });
  }),

  http.get(`${API_BASE_URL}/api/v1/audit/logs/:id`, ({ params }) => {
    const log = mockAuditLogs.find((l) => l.id === params.id);
    if (!log) {
      return new HttpResponse(null, { status: 404 });
    }
    return HttpResponse.json(log);
  }),

  // Error simulation endpoint for testing error handling
  http.get(`${API_BASE_URL}/api/v1/error-test`, () => {
    return HttpResponse.json(
      { error: 'Internal Server Error', message: 'Something went wrong' },
      { status: 500 }
    );
  }),

  // Unauthorized endpoint for testing auth handling
  http.get(`${API_BASE_URL}/api/v1/unauthorized`, () => {
    return HttpResponse.json({ error: 'Unauthorized', message: 'Invalid token' }, { status: 401 });
  }),
];
