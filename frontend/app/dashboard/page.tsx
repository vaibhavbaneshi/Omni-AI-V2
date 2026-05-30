"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { useMemo } from "react";
import {
  Activity,
  ArrowRight,
  BarChart3,
  Brain,
  Calendar,
  ChevronDown,
  ChevronRight,
  Clock,
  Command,
  Cpu,
  Database,
  FileText,
  Gauge,
  Layers3,
  LogOut,
  MessageSquare,
  Plus,
  Radio,
  Settings,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Users,
  Zap,
} from "lucide-react";
import { useRouter } from "next/navigation";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { DropdownMenu, DropdownMenuContent, DropdownMenuGroup, DropdownMenuItem, DropdownMenuSeparator, DropdownMenuTrigger } from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { clearSession, getInitials, useRequireAuth } from "@/lib/auth";
import { formatCount, useAnalytics } from "@/hooks/useAnalytics";
import { cn } from "@/lib/utils";

const quickActions = [
  {
    title: "Start New Chat",
    description: "Open a fresh reasoning workspace",
    icon: MessageSquare,
    href: "/chat",
    accent: "text-primary bg-primary/10",
  },
  {
    title: "Upload Document",
    description: "Parse PDFs, specs, and notes",
    icon: FileText,
    href: "/chat",
    accent: "text-cyan-300 bg-cyan-400/10",
  },
  {
    title: "View Analytics",
    description: "Inspect usage and throughput",
    icon: BarChart3,
    href: "/dashboard",
    accent: "text-emerald-300 bg-emerald-400/10",
  },
  {
    title: "Manage Models",
    description: "Tune routing and defaults",
    icon: Brain,
    href: "/settings",
    accent: "text-amber-300 bg-amber-400/10",
  },
];

const fadeIn = {
  initial: { opacity: 0, y: 18 },
  animate: { opacity: 1, y: 0 },
};

export default function DashboardPage() {
  const router = useRouter();
  const { session, ready, authenticated } = useRequireAuth();
  const { overview, platform, sessions, loading, error } = useAnalytics(session?.token, 30);

  const stats = useMemo(() => {
    if (!overview) return [];
    const topModel = overview.ai.model_breakdown[0]?.model ?? "—";
    return [
      {
        title: "Messages",
        value: formatCount(overview.users.messages ?? 0),
        change: `${overview.period_days}d`,
        detail: `${overview.users.sessions ?? 0} sessions`,
        icon: MessageSquare,
        accent: "text-primary bg-primary/10 ring-primary/20",
      },
      {
        title: "Documents",
        value: formatCount(overview.rag.uploads),
        change: "Indexed",
        detail: `${overview.rag.ingestion_runs} ingest runs`,
        icon: FileText,
        accent: "text-cyan-300 bg-cyan-400/10 ring-cyan-300/20",
      },
      {
        title: "Tokens Used",
        value: formatCount(overview.ai.total_tokens),
        change: topModel,
        detail: `${overview.ai.avg_latency_ms}ms avg latency`,
        icon: Zap,
        accent: "text-amber-300 bg-amber-400/10 ring-amber-300/20",
      },
      {
        title: platform ? "Active Users" : "API Requests",
        value: formatCount(
          platform?.users.active_users_24h ?? overview.users.api_requests ?? 0
        ),
        change: platform ? "24h" : "Period",
        detail: platform
          ? `${platform.users.total_users ?? 0} total users`
          : "Your workspace traffic",
        icon: Users,
        accent: "text-emerald-300 bg-emerald-400/10 ring-emerald-300/20",
      },
    ];
  }, [overview, platform]);

  const systemSignals = useMemo(() => {
    if (!overview) return [];
    return [
      {
        label: "Avg latency",
        value: `${overview.ai.avg_latency_ms}ms`,
        icon: Gauge,
      },
      {
        label: "Token volume",
        value: formatCount(overview.ai.total_tokens),
        icon: Brain,
      },
      {
        label: "RAG uploads",
        value: String(overview.rag.uploads),
        icon: Database,
      },
    ];
  }, [overview]);

  const modelColors = ["bg-primary", "bg-cyan-300", "bg-emerald-300", "bg-amber-300", "bg-violet-300"];
  const usageByModel = (overview?.ai.model_breakdown ?? []).map((item, index) => ({
    model: item.model,
    usage: item.share_pct,
    color: modelColors[index % modelColors.length],
  }));

  const tokenChartData = overview?.ai.daily_tokens ?? [];

  if (!ready || !authenticated) {
    return <div className="min-h-screen bg-background" />;
  }

  const displayName = session?.name?.split(" ")[0] || "John";
  const initials = getInitials(session?.name);

  const handleLogout = () => {
    clearSession();
    router.replace("/");
  };

  return (
    <div className="min-h-screen overflow-x-hidden bg-background text-foreground">
      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.035)_1px,transparent_1px)] bg-[size:48px_48px] opacity-20" />
      <header className="sticky top-0 z-40 border-b border-white/10 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3 sm:gap-4">
            <Link href="/" className="flex min-w-0 items-center gap-2">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/15 ring-1 ring-primary/25">
                <Sparkles className="size-5 text-primary" />
              </div>
              <span className="truncate text-lg font-semibold sm:text-xl">Omni AI</span>
            </Link>
            <Separator orientation="vertical" className="hidden h-6 sm:block" />
            <Badge variant="outline" className="hidden border-emerald-300/20 bg-emerald-400/10 text-emerald-200 sm:inline-flex">
              <Radio className="mr-1 size-3" />
              Command center online
            </Badge>
          </div>

          <div className="flex items-center gap-2 sm:gap-3">
            <Link
              href="/chat"
              className={cn(buttonVariants({ variant: "outline", size: "sm" }), "border-white/10 bg-white/[0.03] hover:bg-white/[0.07]")}
            >
                <Plus data-icon="inline-start" />
                New Chat
            </Link>
            <Link href="/settings" aria-label="Settings" className={buttonVariants({ variant: "ghost", size: "icon" })}>
              <Settings className="size-4" />
            </Link>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button className="flex items-center gap-2 rounded-full ring-1 ring-white/10 px-1.5 py-1 transition hover:ring-primary/40 focus:outline-none focus:ring-2 focus:ring-primary/50">
                  <Avatar className="size-8">
                    <AvatarFallback className="bg-primary/15 text-sm text-primary">{initials}</AvatarFallback>
                  </Avatar>
                  <ChevronDown className="size-4 text-muted-foreground" />
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="w-56">
                <DropdownMenuGroup>
                  <DropdownMenuItem asChild>
                    <Link href="/settings">
                      <Settings data-icon="inline-start" />
                      Settings
                    </Link>
                  </DropdownMenuItem>
                </DropdownMenuGroup>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleLogout} className="text-destructive">
                  <LogOut data-icon="inline-start" />
                  Sign Out
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-7xl space-y-6 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        {error && (
          <div className="rounded-lg border border-destructive/30 bg-destructive/10 px-4 py-3 text-sm text-destructive">
            {error}
          </div>
        )}

        {loading && !overview && (
          <div className="rounded-lg border border-white/10 bg-card/50 px-4 py-8 text-center text-sm text-muted-foreground">
            Loading analytics…
          </div>
        )}

        <motion.section
          {...fadeIn}
          className="grid gap-4 rounded-lg border border-white/10 bg-card/70 p-4 shadow-premium backdrop-blur-xl sm:p-6 lg:grid-cols-[1.4fr_0.6fr]"
        >
          <div className="space-y-5">
            <div className="flex flex-wrap items-center gap-2">
              <Badge className="bg-primary/15 text-primary hover:bg-primary/20">Pro workspace</Badge>
              <Badge variant="outline" className="border-white/10 bg-white/[0.03] text-muted-foreground">
                <ShieldCheck className="mr-1 size-3" />
                Secure routing active
              </Badge>
            </div>
            <div className="max-w-3xl space-y-3">
              <h1 className="text-3xl font-semibold leading-tight sm:text-4xl lg:text-5xl">
                Good evening, {displayName}. Your AI operating layer is synchronized.
              </h1>
              <p className="max-w-2xl text-sm leading-6 text-muted-foreground sm:text-base">
                Monitor model traffic, agent workload, billing capacity, and knowledge flow from one high-signal control surface.
              </p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <Link href="/chat" className={cn(buttonVariants(), "h-10 bg-primary shadow-[0_0_28px_-12px_oklch(0.65_0.25_275)] hover:bg-primary/90")}>
                <Command data-icon="inline-start" />
                Launch Workspace
              </Link>
              <Link
                href="/settings"
                className={cn(buttonVariants({ variant: "outline" }), "h-10 border-white/10 bg-white/[0.03] hover:bg-white/[0.07]")}
              >
                Tune System
                <ArrowRight data-icon="inline-end" />
              </Link>
            </div>
          </div>

          <div className="grid content-between gap-3 rounded-lg border border-white/10 bg-background/40 p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Neural throughput</p>
                <p className="text-xs text-muted-foreground">Last 24 hours</p>
              </div>
              <Activity className="size-5 text-emerald-300" />
            </div>
            <div className="space-y-3">
              {systemSignals.map((signal) => (
                <div key={signal.label} className="flex items-center justify-between rounded-lg bg-white/[0.035] px-3 py-2 ring-1 ring-white/5">
                  <div className="flex items-center gap-2 text-sm text-muted-foreground">
                    <signal.icon className="size-4 text-foreground" />
                    {signal.label}
                  </div>
                  <span className="font-mono text-sm text-foreground">{signal.value}</span>
                </div>
              ))}
            </div>
          </div>
        </motion.section>

        <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat, index) => (
            <motion.div key={stat.title} {...fadeIn} transition={{ delay: index * 0.06 }}>
              <Card className="h-full rounded-lg border-white/10 bg-card/65 py-0 shadow-premium transition-all duration-300 hover:-translate-y-0.5 hover:border-primary/30 hover:bg-card/90">
                <CardContent className="p-4">
                  <div className="mb-5 flex items-start justify-between">
                    <div className={`flex size-10 items-center justify-center rounded-lg ring-1 ${stat.accent}`}>
                      <stat.icon className="size-5" />
                    </div>
                    <Badge variant="outline" className="border-white/10 bg-white/[0.03] text-xs text-emerald-200">
                      <TrendingUp className="mr-1 size-3" />
                      {stat.change}
                    </Badge>
                  </div>
                  <p className="text-2xl font-semibold leading-none">{stat.value}</p>
                  <p className="mt-2 text-sm font-medium">{stat.title}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{stat.detail}</p>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </section>

        {tokenChartData.length > 0 && (
          <motion.section {...fadeIn} transition={{ delay: 0.2 }}>
            <Card className="rounded-lg border-white/10 bg-card/65 shadow-premium">
              <CardHeader>
                <CardTitle className="text-lg">Token Usage</CardTitle>
                <CardDescription>Daily token consumption over the last {overview?.period_days ?? 30} days</CardDescription>
              </CardHeader>
              <CardContent className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={tokenChartData}>
                    <defs>
                      <linearGradient id="tokenGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="oklch(0.65 0.25 275)" stopOpacity={0.35} />
                        <stop offset="95%" stopColor="oklch(0.65 0.25 275)" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                    <XAxis dataKey="date" tick={{ fill: "#888", fontSize: 11 }} />
                    <YAxis tick={{ fill: "#888", fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        background: "rgba(10,10,15,0.95)",
                        border: "1px solid rgba(255,255,255,0.1)",
                        borderRadius: 8,
                      }}
                    />
                    <Area type="monotone" dataKey="tokens" stroke="oklch(0.65 0.25 275)" fill="url(#tokenGradient)" />
                  </AreaChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          </motion.section>
        )}

        <section className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1.55fr)_minmax(320px,0.85fr)]">
          <motion.div {...fadeIn} transition={{ delay: 0.25 }}>
            <Card className="rounded-lg border-white/10 bg-card/65 shadow-premium">
              <CardHeader className="flex flex-row items-center justify-between gap-4 px-4 sm:px-5">
                <div>
                  <CardTitle className="text-lg">Conversation Operations</CardTitle>
                  <CardDescription>Recent threads, states, and model routing</CardDescription>
                </div>
                <Link href="/chat" className={buttonVariants({ variant: "ghost", size: "sm" })}>
                  View all
                  <ChevronRight data-icon="inline-end" />
                </Link>
              </CardHeader>
              <CardContent className="px-2 pb-3 sm:px-3">
                <div className="space-y-1">
                  {(sessions.length ? sessions.slice(0, 6) : []).map((chat) => (
                    <Link
                      key={chat.id}
                      href={`/chat?id=${chat.id}`}
                      className="group grid gap-3 rounded-lg p-3 transition-all duration-200 hover:bg-white/[0.045] sm:grid-cols-[auto_minmax(0,1fr)_auto] sm:items-center"
                    >
                      <div className="flex size-10 items-center justify-center rounded-lg bg-white/[0.04] ring-1 ring-white/10 transition-colors group-hover:bg-primary/10 group-hover:text-primary">
                        <MessageSquare className="size-5" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex min-w-0 flex-wrap items-center gap-2">
                          <p className="truncate font-medium group-hover:text-primary">{chat.title}</p>
                        </div>
                        <p className="mt-1 truncate text-sm text-muted-foreground">Session #{chat.id}</p>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground sm:justify-end">
                        <Clock className="size-3" />
                        Open
                      </div>
                    </Link>
                  ))}
                  {!sessions.length && !loading && (
                    <p className="px-3 py-6 text-center text-sm text-muted-foreground">No chats yet. Start a conversation to see activity here.</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          <motion.div {...fadeIn} transition={{ delay: 0.3 }} className="grid gap-5">
            <Card className="rounded-lg border-white/10 bg-card/65 shadow-premium">
              <CardHeader>
                <CardTitle className="text-lg">Model Mix</CardTitle>
                <CardDescription>This month&apos;s inference distribution</CardDescription>
              </CardHeader>
              <CardContent className="space-y-5">
                <div className="space-y-4">
                  {usageByModel.length ? usageByModel.map((item) => (
                    <div key={item.model} className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium truncate pr-2">{item.model}</span>
                        <span className="font-mono text-muted-foreground">{item.usage}%</span>
                      </div>
                      <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
                        <motion.div
                          className={`h-full rounded-full ${item.color}`}
                          initial={{ width: 0 }}
                          animate={{ width: `${item.usage}%` }}
                          transition={{ duration: 0.8, delay: 0.35 }}
                        />
                      </div>
                    </div>
                  )) : (
                    <p className="text-sm text-muted-foreground">No model usage recorded yet.</p>
                  )}
                </div>

                <Separator />

                <div className="grid gap-3 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Period</span>
                    <span>{overview?.period_days ?? 30} days</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">Total tokens</span>
                    <span className="font-medium">{formatCount(overview?.ai.total_tokens ?? 0)}</span>
                  </div>
                  {platform && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">Platform users</span>
                      <span>{platform.users.total_users ?? 0}</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            {platform?.ai.endpoint_latency && platform.ai.endpoint_latency.length > 0 && (
              <Card className="rounded-lg border-white/10 bg-card/65 shadow-premium">
                <CardHeader>
                  <CardTitle className="text-lg">Endpoint Latency</CardTitle>
                  <CardDescription>Admin view — top API paths by volume</CardDescription>
                </CardHeader>
                <CardContent className="h-56">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={platform.ai.endpoint_latency.slice(0, 6)} layout="vertical" margin={{ left: 8 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
                      <XAxis type="number" tick={{ fill: "#888", fontSize: 10 }} unit="ms" />
                      <YAxis type="category" dataKey="path" width={100} tick={{ fill: "#888", fontSize: 10 }} />
                      <Tooltip
                        contentStyle={{
                          background: "rgba(10,10,15,0.95)",
                          border: "1px solid rgba(255,255,255,0.1)",
                          borderRadius: 8,
                        }}
                      />
                      <Bar dataKey="avg_latency_ms" fill="oklch(0.75 0.15 160)" radius={4} />
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
            )}
          </motion.div>
        </section>

        <motion.section {...fadeIn} transition={{ delay: 0.35 }} className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">Command Modules</h2>
              <p className="text-sm text-muted-foreground">Fast paths for the work you repeat most.</p>
            </div>
            <Layers3 className="hidden size-5 text-muted-foreground sm:block" />
          </div>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {quickActions.map((action) => (
              <Link key={action.title} href={action.href} className="group">
                <Card className="h-full rounded-lg border-white/10 bg-card/55 py-0 shadow-premium transition-all duration-300 hover:-translate-y-0.5 hover:border-primary/30 hover:bg-card/85">
                  <CardContent className="p-4">
                    <div className={`mb-4 flex size-11 items-center justify-center rounded-lg ${action.accent} ring-1 ring-white/10`}>
                      <action.icon className="size-5" />
                    </div>
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="font-medium transition-colors group-hover:text-primary">{action.title}</h3>
                      <ArrowRight className="size-4 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-primary" />
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">{action.description}</p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </motion.section>

        <motion.section
          {...fadeIn}
          transition={{ delay: 0.4 }}
          className="grid gap-3 rounded-lg border border-white/10 bg-card/50 p-4 shadow-premium sm:grid-cols-3"
        >
          {[
            { label: "Next calibration", value: "Today, 22:00", icon: Calendar },
            { label: "Policy guardrails", value: "14 active", icon: ShieldCheck },
            { label: "Compute fabric", value: "Nominal", icon: Cpu },
          ].map((item) => (
            <div key={item.label} className="flex items-center gap-3 rounded-lg bg-white/[0.03] p-3 ring-1 ring-white/5">
              <div className="flex size-9 items-center justify-center rounded-lg bg-background/70">
                <item.icon className="size-4 text-primary" />
              </div>
              <div>
                <p className="text-xs text-muted-foreground">{item.label}</p>
                <p className="text-sm font-medium">{item.value}</p>
              </div>
            </div>
          ))}
        </motion.section>
      </main>
    </div>
  );
}
