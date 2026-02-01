/**
 * Authentication feature type definitions.
 *
 * Types for login forms, auth state management, and session handling.
 *
 * @module features/auth/types
 */

import type { UserProfile, AuthSession } from "@/types/user";

/**
 * Login form input data.
 */
export interface LoginFormData {
  /** User's email or username */
  email: string;
  /** User's password */
  password: string;
  /** Remember login session */
  rememberMe?: boolean;
}

/**
 * Login form validation errors.
 */
export interface LoginFormErrors {
  email?: string;
  password?: string;
  general?: string;
}

/**
 * OAuth provider information.
 */
export interface OAuthProvider {
  /** Provider ID (e.g., "identity-service") */
  id: string;
  /** Provider display name */
  name: string;
  /** Provider type */
  type: "oidc" | "oauth2" | "credentials";
  /** Sign-in URL */
  signinUrl: string;
  /** Callback URL */
  callbackUrl: string;
}

/**
 * Authentication context state.
 */
export interface AuthContextState extends AuthSession {
  /** Sign in with OAuth provider */
  signIn: (provider?: string, options?: SignInOptions) => Promise<void>;
  /** Sign out and clear session */
  signOut: (options?: SignOutOptions) => Promise<void>;
  /** Update user profile */
  updateProfile: (data: Partial<UserProfile>) => Promise<void>;
  /** Check if user has specific role */
  hasRole: (role: string) => boolean;
  /** Check if user has specific permission */
  hasPermission: (permission: string) => boolean;
}

/**
 * Sign-in options.
 */
export interface SignInOptions {
  /** Redirect URL after sign-in */
  callbackUrl?: string;
  /** Whether to redirect (default: true) */
  redirect?: boolean;
}

/**
 * Sign-out options.
 */
export interface SignOutOptions {
  /** Redirect URL after sign-out */
  callbackUrl?: string;
  /** Whether to redirect (default: true) */
  redirect?: boolean;
}

/**
 * Auth guard props for protected routes.
 */
export interface AuthGuardProps {
  /** Child components to render if authorized */
  children: React.ReactNode;
  /** Required roles (any match allows access) */
  requiredRoles?: string[];
  /** Required permissions (any match allows access) */
  requiredPermissions?: string[];
  /** Fallback component when unauthorized */
  fallback?: React.ReactNode;
  /** Redirect URL when unauthorized */
  redirectTo?: string;
}

/**
 * Auth error types.
 */
export type AuthErrorType =
  | "AccessDenied"
  | "Verification"
  | "Configuration"
  | "OAuthSignin"
  | "OAuthCallback"
  | "OAuthCreateAccount"
  | "EmailCreateAccount"
  | "Callback"
  | "OAuthAccountNotLinked"
  | "EmailSignin"
  | "CredentialsSignin"
  | "SessionRequired"
  | "RefreshAccessTokenError"
  | "Default";

/**
 * Auth error state.
 */
export interface AuthError {
  /** Error type */
  type: AuthErrorType;
  /** Human-readable error message */
  message: string;
  /** Original error cause */
  cause?: Error;
}
