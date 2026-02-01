/**
 * Auth Layout - Layout for authentication pages (login, register, etc.)
 *
 * This layout does NOT include the AuthProvider/QueryProvider
 * since those are already provided by the root layout.
 * 
 * Authentication pages use a minimal layout without navigation
 * to provide a clean, focused user experience.
 */

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {children}
    </div>
  );
}
