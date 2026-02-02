/**
 * NextAuth.js v5 configuration for Identity Service OIDC integration.
 *
 * This module configures OAuth 2.0/OIDC authentication with the custom
 * Identity Service, including PKCE, token refresh, and session management.
 *
 * @module libs/auth
 */

import NextAuth from "next-auth";
import type { NextAuthConfig, Profile, User } from "next-auth";

// Environment configuration
const IDENTITY_SERVICE_URL =
  process.env.IDENTITY_SERVICE_URL || "http://localhost:8003";
const OAUTH_CLIENT_ID = process.env.OAUTH_CLIENT_ID || "webshell-frontend";

/**
 * Refresh an expired access token using the refresh_token grant.
 *
 * @param token - Current JWT token with refresh token
 * @returns Updated token with new access token or error
 */
async function refreshAccessToken(token: Record<string, unknown>): Promise<Record<string, unknown>> {
  try {
    const response = await fetch(`${IDENTITY_SERVICE_URL}/oauth2/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "refresh_token",
        refresh_token: token.refreshToken as string,
        client_id: OAUTH_CLIENT_ID,
      }),
    });

    const tokens = await response.json();

    if (!response.ok) {
      console.error("Token refresh failed:", tokens);
      throw new Error(tokens.error_description || tokens.error || "Token refresh failed");
    }

    return {
      ...token,
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token ?? token.refreshToken,
      expiresAt: Math.floor(Date.now() / 1000) + tokens.expires_in,
      error: undefined,
    };
  } catch (error) {
    console.error("Error refreshing access token:", error);
    return {
      ...token,
      error: "RefreshAccessTokenError",
    };
  }
}

/**
 * NextAuth.js configuration for Identity Service OIDC.
 */
export const authConfig: NextAuthConfig = {
  providers: [
    {
      id: "identity-service",
      name: "Identity Service",
      type: "oidc",

      // OIDC Discovery - auto-configures endpoints from .well-known
      issuer: IDENTITY_SERVICE_URL,
      wellKnown: `${IDENTITY_SERVICE_URL}/.well-known/openid-configuration`,

      // Client configuration (PUBLIC client - no secret)
      clientId: OAUTH_CLIENT_ID,
      clientSecret: "", // Empty for public clients

      // Authorization parameters
      authorization: {
        params: {
          scope: "openid profile email offline_access",
          response_type: "code",
        },
      },

      // Token endpoint configuration for public clients
      token: {
        params: {
          client_id: OAUTH_CLIENT_ID,
        },
      },

      // Map OIDC claims to NextAuth user
      profile(profile: Profile): User {
        return {
          id: profile.sub!,
          email: profile.email!,
          name:
            profile.name ??
            profile.preferred_username ??
            profile.email!.split("@")[0],
          image: profile.picture ?? undefined,
        };
      },
    },
  ],

  callbacks: {
    /**
     * JWT callback - handles token storage and refresh.
     */
    async jwt({ token, account, profile }) {
      // Initial sign in - store tokens
      if (account && profile) {
        return {
          ...token,
          accessToken: account.access_token,
          refreshToken: account.refresh_token,
          idToken: account.id_token,
          expiresAt: account.expires_at,
          scope: account.scope,
          sub: profile.sub,
          emailVerified: profile.email_verified,
        };
      }

      // Return previous token if not expired (with 60s buffer)
      const expiresAt = token.expiresAt as number | undefined;
      if (expiresAt && Date.now() < (expiresAt - 60) * 1000) {
        return token;
      }

      // Refresh token if expired
      console.log("Access token expired, refreshing...");
      return refreshAccessToken(token);
    },

    /**
     * Session callback - expose accessToken to client.
     */
    async session({ session, token }) {
      return {
        ...session,
        accessToken: token.accessToken as string | undefined,
        error: token.error as string | undefined,
        user: {
          ...session.user,
          id: token.sub as string,
        },
      };
    },

    /**
     * Authorized callback - protect routes.
     */
    authorized({ auth, request: { nextUrl } }) {
      const isLoggedIn = !!auth?.user;
      const isOnDashboard = nextUrl.pathname.startsWith("/dashboard");
      const isOnAdmin = nextUrl.pathname.startsWith("/admin");
      const isProtected = isOnDashboard || isOnAdmin;

      if (isProtected) {
        if (isLoggedIn) return true;
        return false; // Redirect to login
      }

      return true;
    },
  },

  pages: {
    signIn: "/login",
    signOut: "/logout",
    error: "/auth/error",
  },

  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },

  // Enable debug logging in development
  debug: process.env.NODE_ENV === "development",
};

// Export NextAuth handlers and utilities
export const { handlers, auth, signIn, signOut } = NextAuth(authConfig);

// Legacy alias for getServerSession compatibility
export const authOptions = authConfig;
