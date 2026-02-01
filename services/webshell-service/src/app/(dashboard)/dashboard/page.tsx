"use client";

import { useSession } from "next-auth/react";
import Link from "next/link";
import {
  Users,
  FileText,
  Building2,
  Activity,
  ArrowUpRight,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import { AppHeader } from "@/components/layout/app-header";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useTenant } from "@/contexts/tenant-context";

/**
 * Dashboard Home Page
 *
 * This is the main landing page after authentication.
 * Shows a welcome message and quick stats/actions.
 */

interface StatCardProps {
  title: string;
  value: string | number;
  description: string;
  trend?: {
    value: number;
    isPositive: boolean;
  };
  icon: React.ComponentType<{ className?: string }>;
}

function StatCard({ title, value, description, trend, icon: Icon }: StatCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {title}
        </CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          {trend && (
            <span className={`flex items-center ${trend.isPositive ? "text-green-600" : "text-red-600"}`}>
              {trend.isPositive ? (
                <TrendingUp className="h-3 w-3 mr-1" />
              ) : (
                <TrendingDown className="h-3 w-3 mr-1" />
              )}
              {trend.value}%
            </span>
          )}
          <span>{description}</span>
        </div>
      </CardContent>
    </Card>
  );
}

interface QuickActionProps {
  title: string;
  description: string;
  href: string;
  icon: React.ComponentType<{ className?: string }>;
}

function QuickAction({ title, description, href, icon: Icon }: QuickActionProps) {
  return (
    <Link href={href}>
      <Card className="transition-colors hover:bg-accent">
        <CardContent className="flex items-center gap-4 p-4">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <Icon className="h-5 w-5 text-primary" />
          </div>
          <div className="flex-1">
            <h3 className="font-medium">{title}</h3>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
          <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
        </CardContent>
      </Card>
    </Link>
  );
}

export default function DashboardPage() {
  const { data: session } = useSession();
  const { currentTenant } = useTenant();

  const stats: StatCardProps[] = [
    {
      title: "Total Users",
      value: "1,234",
      description: "from last month",
      trend: { value: 12, isPositive: true },
      icon: Users,
    },
    {
      title: "Active Sessions",
      value: "567",
      description: "currently online",
      trend: { value: 8, isPositive: true },
      icon: Activity,
    },
    {
      title: "Audit Events",
      value: "8,901",
      description: "this month",
      trend: { value: 3, isPositive: false },
      icon: FileText,
    },
    {
      title: "Tenants",
      value: "12",
      description: "organizations",
      icon: Building2,
    },
  ];

  const quickActions: QuickActionProps[] = [
    {
      title: "View Audit Logs",
      description: "Monitor system activity",
      href: "/dashboard/audit",
      icon: FileText,
    },
    {
      title: "Manage Users",
      description: "Add or edit users",
      href: "/dashboard/users",
      icon: Users,
    },
    {
      title: "Manage Tenants",
      description: "Configure organizations",
      href: "/dashboard/tenants",
      icon: Building2,
    },
  ];

  return (
    <>
      <AppHeader
        breadcrumbs={[
          { label: "Dashboard", href: "/dashboard" },
          { label: "Overview" },
        ]}
      />
      <div className="flex-1 space-y-6 p-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold tracking-tight">
              Welcome back, {session?.user?.name || "User"}!
            </h1>
            <p className="text-muted-foreground">
              Here&apos;s what&apos;s happening with your platform today.
            </p>
          </div>
          {currentTenant && (
            <Badge variant="secondary" className="text-sm">
              <Building2 className="h-3 w-3 mr-1" />
              {currentTenant.name}
            </Badge>
          )}
        </div>

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => (
            <StatCard key={stat.title} {...stat} />
          ))}
        </div>

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>
              Common tasks and shortcuts for your workflow
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-3">
              {quickActions.map((action) => (
                <QuickAction key={action.href} {...action} />
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Recent Activity Placeholder */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between">
            <div>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>Latest events across your platform</CardDescription>
            </div>
            <Button variant="outline" size="sm" asChild>
              <Link href="/dashboard/audit">View All</Link>
            </Button>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Placeholder activity items */}
              {[1, 2, 3].map((i) => (
                <div key={i} className="flex items-center gap-4 rounded-lg border p-4">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-muted">
                    <Activity className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-medium">User login detected</p>
                    <p className="text-xs text-muted-foreground">
                      {i} hour{i > 1 ? "s" : ""} ago
                    </p>
                  </div>
                  <Badge variant="outline">Authentication</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Session Debug Info (Development Only) */}
        {process.env.NODE_ENV === "development" && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">Session Debug Info</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="overflow-auto rounded bg-muted p-4 text-xs">
                {JSON.stringify(session, null, 2)}
              </pre>
            </CardContent>
          </Card>
        )}
      </div>
    </>
  );
}

