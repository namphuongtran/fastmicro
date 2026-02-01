/**
 * Authentication provider for client components.
 *
 * Wraps the application with NextAuth SessionProvider
 * to enable authentication state in client components.
 *
 * @module components/providers/auth-provider
 */

"use client";

import { SessionProvider } from "next-auth/react";
import type { Session } from "next-auth";

interface AuthProviderProps {
  /** Child components */
  children: React.ReactNode;
  /** Initial session (from server) */
  session?: Session | null;
}

/**
 * Authentication provider component.
 *
 * Wrap your application with this provider to enable
 * useSession, signIn, and signOut in client components.
 *
 * @example
 * ```tsx
 * // In app/layout.tsx
 * export default function RootLayout({ children }) {
 *   return (
 *     <html>
 *       <body>
 *         <AuthProvider>
 *           {children}
 *         </AuthProvider>
 *       </body>
 *     </html>
 *   );
 * }
 * ```
 */
export function AuthProvider({ children, session }: AuthProviderProps) {
  return (
    <SessionProvider
      session={session}
      // Refetch session every 5 minutes
      refetchInterval={5 * 60}
      // Refetch session on window focus
      refetchOnWindowFocus={true}
    >
      {children}
    </SessionProvider>
  );
}
