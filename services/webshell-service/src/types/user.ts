/**
 * User and authentication type definitions.
 *
 * Mirrors the Identity Service user claims and provides
 * TypeScript types for the frontend authentication layer.
 *
 * @module types/user
 */

/**
 * User profile from OIDC claims.
 * Based on standard OIDC profile scope claims.
 */
export interface UserProfile {
  /** Unique user identifier (OIDC subject) */
  id: string;
  /** User's email address */
  email: string;
  /** Whether email is verified */
  emailVerified: boolean;
  /** Display name */
  name: string;
  /** Given (first) name */
  givenName?: string;
  /** Family (last) name */
  familyName?: string;
  /** Preferred username */
  preferredUsername?: string;
  /** Profile picture URL */
  picture?: string;
  /** Locale preference */
  locale?: string;
  /** Timezone */
  zoneinfo?: string;
  /** Last profile update timestamp */
  updatedAt?: number;
}

/**
 * User's role within a tenant.
 */
export type TenantRole = "owner" | "admin" | "member" | "viewer";

/**
 * User's tenant membership.
 */
export interface TenantMembership {
  /** Tenant ID */
  tenantId: string;
  /** Tenant name */
  tenantName: string;
  /** User's role in this tenant */
  role: TenantRole;
  /** When the user joined this tenant */
  joinedAt: string;
}

/**
 * Full user context including profile and tenant memberships.
 */
export interface UserContext extends UserProfile {
  /** User's tenant memberships */
  tenants: TenantMembership[];
  /** Currently active tenant ID */
  activeTenantId?: string;
  /** Global roles (admin, user, etc.) */
  roles: string[];
  /** Granted permissions */
  permissions: string[];
}

/**
 * Authentication session state.
 */
export interface AuthSession {
  /** Whether user is authenticated */
  isAuthenticated: boolean;
  /** Whether session is loading */
  isLoading: boolean;
  /** User profile if authenticated */
  user: UserProfile | null;
  /** Access token for API calls */
  accessToken: string | null;
  /** Session error state */
  error: string | null;
}

/**
 * OAuth token response from Identity Service.
 */
export interface TokenResponse {
  /** Access token for API authorization */
  access_token: string;
  /** Token type (always "Bearer") */
  token_type: "Bearer";
  /** Token expiration in seconds */
  expires_in: number;
  /** Refresh token for obtaining new access tokens */
  refresh_token?: string;
  /** Granted scopes */
  scope?: string;
  /** ID token with user claims (for OIDC flows) */
  id_token?: string;
}

/**
 * Decoded JWT token payload.
 */
export interface JWTPayload {
  /** Issuer */
  iss: string;
  /** Subject (user ID) */
  sub: string;
  /** Audience */
  aud: string | string[];
  /** Expiration timestamp */
  exp: number;
  /** Issued at timestamp */
  iat: number;
  /** Not before timestamp */
  nbf?: number;
  /** JWT ID */
  jti?: string;
  /** Client ID */
  client_id?: string;
  /** Granted scopes */
  scope?: string;
  /** Tenant ID (custom claim) */
  tid?: string;
  /** User email */
  email?: string;
  /** User name */
  name?: string;
}
