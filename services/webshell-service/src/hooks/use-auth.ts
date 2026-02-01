/**
 * Authentication hook for client components.
 *
 * Provides access to the current authentication session,
 * user profile, and authentication actions.
 *
 * @module hooks/useAuth
 */

"use client";

import { useSession, signIn as nextAuthSignIn, signOut as nextAuthSignOut } from "next-auth/react";
import { useCallback, useMemo } from "react";
import type { AuthSession, UserProfile } from "@/types/user";
import type { SignInOptions, SignOutOptions } from "@/features/auth/types";

/**
 * Return type for useAuth hook.
 */
export interface UseAuthReturn extends AuthSession {
  /** Sign in with OAuth provider */
  signIn: (provider?: string, options?: SignInOptions) => Promise<void>;
  /** Sign out and clear session */
  signOut: (options?: SignOutOptions) => Promise<void>;
  /** Refresh the session */
  refresh: () => Promise<void>;
}

/**
 * Hook for accessing authentication state and actions.
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { isAuthenticated, user, signIn, signOut } = useAuth();
 *
 *   if (!isAuthenticated) {
 *     return <button onClick={() => signIn()}>Sign In</button>;
 *   }
 *
 *   return (
 *     <div>
 *       <p>Welcome, {user?.name}</p>
 *       <button onClick={() => signOut()}>Sign Out</button>
 *     </div>
 *   );
 * }
 * ```
 */
export function useAuth(): UseAuthReturn {
  const { data: session, status, update } = useSession();

  const isLoading = status === "loading";
  const isAuthenticated = status === "authenticated" && !!session?.user;

  // Map NextAuth session to UserProfile
  const user: UserProfile | null = useMemo(() => {
    if (!session?.user) return null;

    return {
      id: session.user.id,
      email: session.user.email ?? "",
      emailVerified: true, // Assume verified if logged in
      name: session.user.name ?? "",
      picture: session.user.image ?? undefined,
    };
  }, [session?.user]);

  // Get access token for API calls
  const accessToken = session?.accessToken ?? null;

  // Get session error state
  const error = session?.error ?? null;

  // Sign in handler
  const signIn = useCallback(
    async (provider = "identity-service", options?: SignInOptions) => {
      await nextAuthSignIn(provider, {
        callbackUrl: options?.callbackUrl ?? "/dashboard",
        redirect: true,
      });
    },
    []
  );

  // Sign out handler
  const signOut = useCallback(async (options?: SignOutOptions) => {
    await nextAuthSignOut({
      callbackUrl: options?.callbackUrl ?? "/",
      redirect: true,
    });
  }, []);

  // Refresh session
  const refresh = useCallback(async () => {
    await update();
  }, [update]);

  return {
    isAuthenticated,
    isLoading,
    user,
    accessToken,
    error,
    signIn,
    signOut,
    refresh,
  };
}

/**
 * Hook for checking authentication status only.
 * Lighter alternative when full auth context is not needed.
 */
export function useIsAuthenticated(): boolean {
  const { status } = useSession();
  return status === "authenticated";
}

/**
 * Hook for checking loading status only.
 */
export function useIsAuthLoading(): boolean {
  const { status } = useSession();
  return status === "loading";
}
