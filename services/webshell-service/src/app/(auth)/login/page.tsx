"use client";

import { signIn, useSession } from "next-auth/react";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState, useCallback, Suspense } from "react";

/**
 * Login Page - Handles OAuth2/OIDC authentication flow
 *
 * Authentication Flow:
 * 1. User lands on /login
 * 2. Check if already authenticated → redirect to dashboard
 * 3. User clicks "Sign In" → initiate OAuth2 PKCE flow
 * 4. Redirect to Identity Service /authorize endpoint
 * 5. User authenticates with Identity Service
 * 6. Callback returns to NextAuth handler
 * 7. User redirected to callbackUrl or dashboard
 */

type AuthError =
  | "Configuration"
  | "AccessDenied"
  | "Verification"
  | "OAuthSignin"
  | "OAuthCallback"
  | "OAuthCreateAccount"
  | "Callback"
  | "SessionRequired"
  | "Default";

const ERROR_MESSAGES: Record<AuthError, string> = {
  Configuration:
    "There is a problem with the server configuration. Please contact support.",
  AccessDenied:
    "Access denied. You do not have permission to access this application.",
  Verification: "The verification link may have expired or already been used.",
  OAuthSignin: "Unable to initiate sign in. Please try again.",
  OAuthCallback: "Authentication callback failed. Please try again.",
  OAuthCreateAccount: "Unable to create your account. Please contact support.",
  Callback: "Authentication callback error. Please try again.",
  SessionRequired: "Please sign in to access this page.",
  Default: "An unexpected error occurred. Please try again.",
};

function LoginContent() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const searchParams = useSearchParams();

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Get error and callback URL from query parameters
  const errorParam = searchParams.get("error") as AuthError | null;
  const callbackUrl = searchParams.get("callbackUrl") || "/dashboard";

  // Redirect if already authenticated
  useEffect(() => {
    if (status === "authenticated" && session) {
      router.replace(callbackUrl);
    }
  }, [status, session, router, callbackUrl]);

  // Set error message from URL parameter
  useEffect(() => {
    if (errorParam) {
      setError(ERROR_MESSAGES[errorParam] || ERROR_MESSAGES.Default);
    }
  }, [errorParam]);

  const handleSignIn = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Initiate OAuth2 PKCE flow with Identity Service
      // With redirect: true, this will redirect the browser
      await signIn("identity-service", {
        callbackUrl,
        redirect: true,
      });
      // If we reach here, redirect didn't happen (shouldn't normally occur)
    } catch (err) {
      console.error("Sign in error:", err);
      setError("Failed to initiate sign in. Please try again.");
      setIsLoading(false);
    }
  }, [callbackUrl]);

  // Show loading while checking session
  if (status === "loading") {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center p-4 bg-gray-50">
        <div className="w-full max-w-md space-y-8">
          <div className="flex flex-col items-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600" />
            <p className="mt-4 text-gray-600">Loading...</p>
          </div>
        </div>
      </main>
    );
  }

  // Don't render login form if authenticated (will redirect)
  if (status === "authenticated") {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center p-4 bg-gray-50">
        <div className="w-full max-w-md space-y-8">
          <div className="flex flex-col items-center">
            <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600" />
            <p className="mt-4 text-gray-600">Redirecting...</p>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4 bg-gray-50">
      <div className="w-full max-w-md space-y-8">
        {/* Logo and Title */}
        <div className="flex flex-col items-center">
          <div className="flex h-16 w-16 items-center justify-center rounded-xl bg-blue-600 text-white text-2xl font-bold">
            W
          </div>
          <h1 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            WebShell
          </h1>
          <p className="mt-2 text-center text-sm text-gray-600">
            Enterprise Dashboard Platform
          </p>
        </div>

        {/* Login Card */}
        <div className="mt-8 bg-white px-6 py-8 shadow-lg rounded-xl border border-gray-100">
          <div className="space-y-6">
            {/* Error Alert */}
            {error && (
              <div
                className="rounded-lg bg-red-50 p-4 border border-red-200"
                role="alert"
                aria-live="polite"
              >
                <div className="flex">
                  <svg
                    className="h-5 w-5 text-red-400 mr-2 flex-shrink-0"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                    aria-hidden="true"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.28 7.22a.75.75 0 00-1.06 1.06L8.94 10l-1.72 1.72a.75.75 0 101.06 1.06L10 11.06l1.72 1.72a.75.75 0 101.06-1.06L11.06 10l1.72-1.72a.75.75 0 00-1.06-1.06L10 8.94 8.28 7.22z"
                      clipRule="evenodd"
                    />
                  </svg>
                  <p className="text-sm text-red-700">{error}</p>
                </div>
              </div>
            )}

            {/* Sign In Description */}
            <div className="text-center">
              <p className="text-sm text-gray-600">
                Sign in with your enterprise credentials to access the
                dashboard.
              </p>
            </div>

            {/* Sign In Button */}
            <button
              onClick={handleSignIn}
              disabled={isLoading}
              className="flex w-full justify-center items-center rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {isLoading ? (
                <>
                  <div className="h-5 w-5 animate-spin rounded-full border-2 border-white border-t-transparent mr-2" />
                  Signing in...
                </>
              ) : (
                <>
                  <svg
                    className="h-5 w-5 mr-2"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1"
                    />
                  </svg>
                  Sign in with Identity Service
                </>
              )}
            </button>
          </div>
        </div>

        {/* Footer */}
        <div className="text-center">
          <p className="text-xs text-gray-500">
            Protected by enterprise-grade security.
            <br />
            By signing in, you agree to our terms of service.
          </p>
        </div>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main className="flex min-h-screen flex-col items-center justify-center p-4 bg-gray-50">
          <div className="w-full max-w-md space-y-8">
            <div className="flex flex-col items-center">
              <div className="h-12 w-12 animate-spin rounded-full border-4 border-gray-200 border-t-blue-600" />
              <p className="mt-4 text-gray-600">Loading...</p>
            </div>
          </div>
        </main>
      }
    >
      <LoginContent />
    </Suspense>
  );
}
