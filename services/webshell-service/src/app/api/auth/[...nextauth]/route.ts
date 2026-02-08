/**
 * NextAuth.js API route handler.
 *
 * This catch-all route handles all NextAuth.js authentication endpoints:
 * - GET/POST /api/auth/signin
 * - GET/POST /api/auth/signout
 * - GET /api/auth/session
 * - GET /api/auth/csrf
 * - GET /api/auth/providers
 * - GET/POST /api/auth/callback/:provider
 *
 * @module app/api/auth/[...nextauth]/route
 */

import { handlers } from "@/lib/auth";

export const { GET, POST } = handlers;
