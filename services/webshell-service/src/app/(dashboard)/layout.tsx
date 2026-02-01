"use client";

import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { SidebarProvider, SidebarInset } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/layout/app-sidebar";
import { Skeleton } from "@/components/ui/skeleton";

/**
 * Dashboard Layout - Protected layout for authenticated users
 *
 * Features:
 * - Automatic redirect to login if not authenticated
 * - Loading state while checking authentication
 * - Responsive sidebar navigation with shadcn/ui
 * - Collapsible sidebar with keyboard shortcut (Ctrl/Cmd + B)
 *
 * All pages under (dashboard) route group will:
 * 1. Be protected by authentication
 * 2. Share the dashboard layout (sidebar, header)
 * 3. Have access to user session via useSession
 */

function DashboardSkeleton() {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar Skeleton */}
      <aside className="hidden w-64 border-r bg-background lg:block">
        <div className="flex h-14 items-center border-b px-6">
          <Skeleton className="h-8 w-32" />
        </div>
        <div className="p-4 space-y-4">
          <Skeleton className="h-10 w-full" />
          {[...Array(6)].map((_, i) => (
            <Skeleton key={i} className="h-9 w-full" />
          ))}
        </div>
      </aside>

      {/* Main Content Skeleton */}
      <div className="flex flex-1 flex-col">
        {/* Header Skeleton */}
        <header className="flex h-14 items-center justify-between border-b bg-background px-6">
          <Skeleton className="h-5 w-48" />
          <div className="flex items-center gap-4">
            <Skeleton className="h-9 w-64 hidden sm:block" />
            <Skeleton className="h-9 w-9 rounded-full" />
          </div>
        </header>

        {/* Content Skeleton */}
        <main className="flex-1 p-6">
          <Skeleton className="h-8 w-64 mb-6" />
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {[...Array(4)].map((_, i) => (
              <Skeleton key={i} className="h-32 rounded-lg" />
            ))}
          </div>
          <Skeleton className="h-96 w-full mt-6 rounded-lg" />
        </main>
      </div>
    </div>
  );
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data: session, status } = useSession();
  const router = useRouter();

  // Redirect to login if not authenticated
  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
    }
  }, [status, router]);

  // Show loading skeleton while checking authentication
  if (status === "loading") {
    return <DashboardSkeleton />;
  }

  // Don't render content if not authenticated (will redirect)
  if (status === "unauthenticated") {
    return <DashboardSkeleton />;
  }

  return (
    <SidebarProvider>
      <AppSidebar />
      <SidebarInset>
        <main className="flex-1">{children}</main>
      </SidebarInset>
    </SidebarProvider>
  );
}
