/**
 * NextAuth.js type extensions for custom session and JWT properties.
 *
 * Extends the default NextAuth types to include:
 * - Access token for API calls
 * - Refresh token for token renewal
 * - Error state for token refresh failures
 * - User ID from OIDC subject claim
 *
 * @module types/next-auth
 */

import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  /**
   * Extended Session interface with access token and error state.
   */
  interface Session {
    /** Access token for authenticating API requests */
    accessToken?: string;
    /** Error state (e.g., "RefreshAccessTokenError") */
    error?: string;
    user: {
      /** User's unique identifier (OIDC subject claim) */
      id: string;
      email: string;
      name: string;
      image?: string;
    };
  }

  /**
   * Extended User interface with optional image.
   */
  interface User {
    id: string;
    email: string;
    name: string;
    image?: string;
  }
}

declare module "next-auth/jwt" {
  /**
   * Extended JWT interface with OAuth tokens and metadata.
   */
  interface JWT {
    /** Access token for API requests */
    accessToken?: string;
    /** Refresh token for obtaining new access tokens */
    refreshToken?: string;
    /** ID token from OIDC */
    idToken?: string;
    /** Token expiration timestamp (Unix seconds) */
    expiresAt?: number;
    /** Granted OAuth scopes */
    scope?: string;
    /** Token refresh error state */
    error?: string;
    /** User subject identifier */
    sub?: string;
    /** Whether email is verified */
    emailVerified?: boolean;
  }
}
