/**
 * Audit API Route Handler
 *
 * Proxies requests to the audit-service backend.
 * Handles authentication, tenant context, and error transformation.
 */
import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";

// Backend service URL from environment
const AUDIT_SERVICE_URL = process.env.AUDIT_SERVICE_URL ?? "http://localhost:8003";

/**
 * Handle all HTTP methods for audit events
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return handleRequest(request, params.path, "GET");
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return handleRequest(request, params.path, "POST");
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return handleRequest(request, params.path, "PUT");
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return handleRequest(request, params.path, "PATCH");
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  return handleRequest(request, params.path, "DELETE");
}

/**
 * Core request handler that proxies to audit-service
 */
async function handleRequest(
  request: NextRequest,
  pathSegments: string[],
  method: string
): Promise<NextResponse> {
  try {
    // Get session for authentication (next-auth v5)
    const session = await auth();

    if (!session?.user) {
      return NextResponse.json(
        { error: "Unauthorized", message: "Authentication required" },
        { status: 401 }
      );
    }

    // Build the backend URL
    const path = pathSegments.join("/");
    const backendUrl = new URL(`/api/v1/audit/${path}`, AUDIT_SERVICE_URL);

    // Forward query parameters
    const searchParams = request.nextUrl.searchParams;
    searchParams.forEach((value, key) => {
      backendUrl.searchParams.set(key, value);
    });

    // Build request headers
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      "X-Request-ID": request.headers.get("X-Request-ID") ?? crypto.randomUUID(),
    };

    // Add tenant context if available
    const tenantId = request.headers.get("X-Tenant-ID");
    if (tenantId) {
      headers["X-Tenant-ID"] = tenantId;
    }

    // Add auth token if available (cast to extended session type)
    const extendedSession = session as typeof session & { accessToken?: string };
    if (extendedSession.accessToken) {
      headers["Authorization"] = `Bearer ${extendedSession.accessToken}`;
    }

    // Forward user context
    if (session.user.id) {
      headers["X-User-ID"] = session.user.id;
    }

    // Prepare request options
    const fetchOptions: RequestInit = {
      method,
      headers,
    };

    // Add body for non-GET requests
    if (method !== "GET" && method !== "HEAD") {
      const body = await request.text();
      if (body) {
        fetchOptions.body = body;
      }
    }

    // Make request to backend
    const response = await fetch(backendUrl.toString(), fetchOptions);

    // Get response data
    const contentType = response.headers.get("content-type");
    let data: unknown;

    if (contentType?.includes("application/json")) {
      data = await response.json();
    } else {
      data = await response.text();
    }

    // Handle error responses
    if (!response.ok) {
      return NextResponse.json(
        {
          error: response.statusText,
          message: typeof data === "object" && data !== null && "detail" in data
            ? (data as { detail: string }).detail
            : "An error occurred",
          statusCode: response.status,
        },
        { status: response.status }
      );
    }

    // Return successful response
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Audit API proxy error:", error);

    // Handle network/connection errors
    if (error instanceof TypeError && error.message.includes("fetch")) {
      return NextResponse.json(
        {
          error: "Service Unavailable",
          message: "Unable to connect to audit service",
          statusCode: 503,
        },
        { status: 503 }
      );
    }

    // Generic error
    return NextResponse.json(
      {
        error: "Internal Server Error",
        message: error instanceof Error ? error.message : "An unexpected error occurred",
        statusCode: 500,
      },
      { status: 500 }
    );
  }
}
