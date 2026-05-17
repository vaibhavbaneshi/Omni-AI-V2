"use client";

import { useState } from "react";
import type { ReactNode } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Brain,
  Check,
  ChevronLeft,
  Copy,
  CreditCard,
  Download,
  Eye,
  EyeOff,
  Key,
  Lock,
  Palette,
  RefreshCw,
  Save,
  Shield,
  SlidersHorizontal,
  Sparkles,
  User,
  Zap,
} from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { getInitials, useRequireAuth } from "@/lib/auth";

const fadeIn = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
};

const settingCards = [
  { label: "Model routing", value: "GPT-4 primary", icon: Brain },
  { label: "Workspace mode", value: "Pro control", icon: SlidersHorizontal },
  { label: "Security posture", value: "Protected", icon: Shield },
];

function Panel({
  title,
  description,
  children,
  className = "",
}: {
  title: string;
  description: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Card className={`rounded-lg border-white/10 bg-card/65 shadow-premium ${className}`}>
      <CardHeader className="px-4 sm:px-5">
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-5 px-4 pb-5 sm:px-5">{children}</CardContent>
    </Card>
  );
}

function ToggleRow({
  title,
  description,
  defaultChecked,
}: {
  title: string;
  description: string;
  defaultChecked?: boolean;
}) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-lg bg-white/[0.03] p-3 ring-1 ring-white/5">
      <div className="space-y-0.5">
        <Label className="text-sm">{title}</Label>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <Switch defaultChecked={defaultChecked} />
    </div>
  );
}

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-white/[0.035] p-4 ring-1 ring-white/5">
      <p className="text-2xl font-semibold">{value}</p>
      <p className="mt-1 text-sm text-muted-foreground">{label}</p>
    </div>
  );
}

export default function SettingsPage() {
  const { session, ready, authenticated } = useRequireAuth();
  const [isSaving, setIsSaving] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);

  const handleSave = async () => {
    setIsSaving(true);
    await new Promise((resolve) => setTimeout(resolve, 1000));
    setIsSaving(false);
  };

  const handleCopyKey = () => {
    navigator.clipboard.writeText("sk-omni-xxxxxxxxxxxxxxxxxxxx");
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  if (!ready || !authenticated) {
    return <div className="min-h-screen bg-background" />;
  }

  const nameParts = (session?.name || "John Doe").split(" ");
  const firstName = nameParts[0] || "John";
  const lastName = nameParts.slice(1).join(" ") || "Doe";
  const email = session?.email || "john@example.com";
  const initials = getInitials(session?.name);

  return (
    <div className="min-h-screen overflow-x-hidden bg-background">
      <div className="pointer-events-none fixed inset-0 bg-[linear-gradient(rgba(255,255,255,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.035)_1px,transparent_1px)] bg-[size:48px_48px] opacity-20" />
      <header className="sticky top-0 z-40 border-b border-white/10 bg-background/80 backdrop-blur-xl">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex min-w-0 items-center gap-3">
            <Link href="/chat" aria-label="Back to chat" className={buttonVariants({ variant: "ghost", size: "icon" })}>
              <ChevronLeft className="size-4" />
            </Link>
            <div className="flex min-w-0 items-center gap-2">
              <div className="flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary/15 ring-1 ring-primary/25">
                <Sparkles className="size-5 text-primary" />
              </div>
              <span className="truncate text-lg font-semibold sm:text-xl">Workspace Settings</span>
            </div>
          </div>

          <Button onClick={handleSave} disabled={isSaving} className="h-9">
            {isSaving ? (
              <>
                <span className="mr-2 size-4 animate-spin rounded-full border-2 border-primary-foreground/30 border-t-primary-foreground" />
                Saving
              </>
            ) : (
              <>
                <Save data-icon="inline-start" />
                Save
              </>
            )}
          </Button>
        </div>
      </header>

      <main className="relative z-10 mx-auto max-w-6xl space-y-6 px-4 py-6 sm:px-6 sm:py-8 lg:px-8">
        <motion.section
          {...fadeIn}
          className="grid gap-4 rounded-lg border border-white/10 bg-card/70 p-4 shadow-premium backdrop-blur-xl sm:p-6 lg:grid-cols-[1fr_auto]"
        >
          <div className="max-w-3xl space-y-3">
            <Badge className="bg-primary/15 text-primary hover:bg-primary/20">System configuration</Badge>
            <h1 className="text-3xl font-semibold leading-tight sm:text-4xl">
              Tune the behavior, access, and economics of your AI workspace.
            </h1>
            <p className="text-sm leading-6 text-muted-foreground sm:text-base">
              Keep profile, model defaults, API access, and billing in one precise command surface.
            </p>
          </div>
          <div className="grid gap-3 sm:grid-cols-3 lg:w-[420px] lg:grid-cols-1">
            {settingCards.map((item) => (
              <div key={item.label} className="flex items-center gap-3 rounded-lg bg-white/[0.035] p-3 ring-1 ring-white/5">
                <div className="flex size-9 items-center justify-center rounded-lg bg-background/70">
                  <item.icon className="size-4 text-primary" />
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">{item.label}</p>
                  <p className="text-sm font-medium">{item.value}</p>
                </div>
              </div>
            ))}
          </div>
        </motion.section>

        <Tabs defaultValue="profile" className="gap-5">
          <TabsList className="grid h-auto w-full grid-cols-2 gap-1 rounded-lg border border-white/10 bg-card/70 p-1 shadow-premium sm:grid-cols-4 lg:w-fit">
            <TabsTrigger value="profile" className="h-10 gap-2 rounded-lg px-3">
              <User className="size-4" />
              <span>Profile</span>
            </TabsTrigger>
            <TabsTrigger value="preferences" className="h-10 gap-2 rounded-lg px-3">
              <Palette className="size-4" />
              <span>AI Controls</span>
            </TabsTrigger>
            <TabsTrigger value="api" className="h-10 gap-2 rounded-lg px-3">
              <Key className="size-4" />
              <span>API</span>
            </TabsTrigger>
            <TabsTrigger value="billing" className="h-10 gap-2 rounded-lg px-3">
              <CreditCard className="size-4" />
              <span>Billing</span>
            </TabsTrigger>
          </TabsList>

          <TabsContent value="profile">
            <motion.div {...fadeIn} className="grid gap-5 lg:grid-cols-[1.25fr_0.75fr]">
              <Panel title="Identity" description="Account details and workspace presence">
                <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
                  <Avatar className="size-20 ring-1 ring-white/10">
                    <AvatarFallback className="bg-primary/15 text-2xl text-primary">{initials}</AvatarFallback>
                  </Avatar>
                  <div className="space-y-2">
                    <Button variant="outline" size="sm" className="border-white/10 bg-white/[0.03] hover:bg-white/[0.07]">
                      Change Avatar
                    </Button>
                    <p className="text-xs text-muted-foreground">JPG, PNG or GIF. Max 2MB.</p>
                  </div>
                </div>

                <Separator />

                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="firstName">First Name</Label>
                    <Input id="firstName" defaultValue={firstName} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="lastName">Last Name</Label>
                    <Input id="lastName" defaultValue={lastName} />
                  </div>
                  <div className="space-y-2 sm:col-span-2">
                    <Label htmlFor="email">Email</Label>
                    <Input id="email" type="email" defaultValue={email} />
                  </div>
                  <div className="space-y-2 sm:col-span-2">
                    <Label htmlFor="bio">Operator Notes</Label>
                    <Textarea id="bio" placeholder="Add context your assistants should know..." className="min-h-24 resize-none" />
                  </div>
                </div>
              </Panel>

              <Panel title="Security" description="Protection and signed-in devices">
                <ToggleRow title="Two-Factor Authentication" description="Require a second factor for sensitive changes" />
                <div className="flex items-center justify-between gap-4 rounded-lg bg-white/[0.03] p-3 ring-1 ring-white/5">
                  <div className="flex items-center gap-3">
                    <Lock className="size-4 text-primary" />
                    <div>
                      <p className="font-medium">Password</p>
                      <p className="text-sm text-muted-foreground">Last changed 30 days ago</p>
                    </div>
                  </div>
                  <Button variant="outline" size="sm" className="border-white/10 bg-white/[0.03] hover:bg-white/[0.07]">
                    Change
                  </Button>
                </div>
                <div className="flex items-center justify-between gap-4 rounded-lg bg-white/[0.03] p-3 ring-1 ring-white/5">
                  <div>
                    <p className="font-medium">Active Sessions</p>
                    <p className="text-sm text-muted-foreground">3 devices currently signed in</p>
                  </div>
                  <Button variant="outline" size="sm" className="border-white/10 bg-white/[0.03] hover:bg-white/[0.07]">
                    Manage
                  </Button>
                </div>
              </Panel>
            </motion.div>
          </TabsContent>

          <TabsContent value="preferences">
            <motion.div {...fadeIn} className="grid gap-5 lg:grid-cols-[1fr_1fr]">
              <Panel title="AI Behavior" description="Defaults for routing, tone, and reasoning">
                <div className="grid gap-4 sm:grid-cols-2">
                  <div className="space-y-2">
                    <Label>Default Model</Label>
                    <Select defaultValue="gpt-4">
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          <SelectItem value="gpt-4">GPT-4 (Recommended)</SelectItem>
                          <SelectItem value="gpt-3.5">GPT-3.5 Turbo</SelectItem>
                          <SelectItem value="claude-3">Claude 3 Opus</SelectItem>
                          <SelectItem value="gemini">Gemini Pro</SelectItem>
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-2">
                    <Label>Response Style</Label>
                    <Select defaultValue="balanced">
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectGroup>
                          <SelectItem value="concise">Concise</SelectItem>
                          <SelectItem value="balanced">Balanced</SelectItem>
                          <SelectItem value="detailed">Detailed</SelectItem>
                        </SelectGroup>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="systemPrompt">Custom System Prompt</Label>
                  <Textarea
                    id="systemPrompt"
                    placeholder="Add custom instructions for the AI..."
                    className="min-h-32 resize-none"
                  />
                  <p className="text-xs text-muted-foreground">Included in new conversations by default.</p>
                </div>

                <div className="grid gap-3">
                  <ToggleRow title="Web Search" description="Enable real-time web context in responses" defaultChecked />
                  <ToggleRow title="Code Execution" description="Allow AI to run controlled code snippets" />
                  <ToggleRow title="Streaming Responses" description="Show responses as they are generated" defaultChecked />
                </div>
              </Panel>

              <div className="grid gap-5">
                <Panel title="Appearance" description="Workspace density and display preferences">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label>Theme</Label>
                      <Select defaultValue="dark">
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectGroup>
                            <SelectItem value="light">Light</SelectItem>
                            <SelectItem value="dark">Dark</SelectItem>
                            <SelectItem value="system">System</SelectItem>
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Font Size</Label>
                      <Select defaultValue="medium">
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectGroup>
                            <SelectItem value="small">Small</SelectItem>
                            <SelectItem value="medium">Medium</SelectItem>
                            <SelectItem value="large">Large</SelectItem>
                          </SelectGroup>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                  <ToggleRow title="Compact Mode" description="Reduce spacing in repeated chat surfaces" />
                </Panel>

                <Panel title="Notifications" description="Operational alerts and product updates">
                  <ToggleRow title="Email Notifications" description="Receive account and workflow updates" defaultChecked />
                  <ToggleRow title="Product Updates" description="News about new features and improvements" defaultChecked />
                  <ToggleRow title="Usage Alerts" description="Warn when approaching limits" defaultChecked />
                </Panel>
              </div>
            </motion.div>
          </TabsContent>

          <TabsContent value="api">
            <motion.div {...fadeIn} className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
              <Panel title="API Keys" description="Programmatic access for trusted services">
                <div className="rounded-lg border border-white/10 bg-white/[0.035] p-4">
                  <div className="mb-4 flex items-center justify-between gap-4">
                    <div>
                      <p className="font-medium">Production Key</p>
                      <p className="text-sm text-muted-foreground">Created on May 1, 2026</p>
                    </div>
                    <Badge className="bg-emerald-400/10 text-emerald-200 hover:bg-emerald-400/15">Active</Badge>
                  </div>
                  <div className="relative">
                    <Input
                      type={showApiKey ? "text" : "password"}
                      value="sk-omni-xxxxxxxxxxxxxxxxxxxx"
                      readOnly
                      className="pr-20 font-mono text-sm"
                    />
                    <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1">
                      <Button variant="ghost" size="icon" className="size-7" onClick={() => setShowApiKey(!showApiKey)} aria-label="Toggle API key visibility">
                        {showApiKey ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                      </Button>
                      <Button variant="ghost" size="icon" className="size-7" onClick={handleCopyKey} aria-label="Copy API key">
                        {copiedKey ? <Check className="size-4 text-success" /> : <Copy className="size-4" />}
                      </Button>
                    </div>
                  </div>
                </div>

                <div className="flex flex-col justify-between gap-4 rounded-lg bg-white/[0.03] p-3 ring-1 ring-white/5 sm:flex-row sm:items-center">
                  <div>
                    <p className="font-medium">Generate New Key</p>
                    <p className="text-sm text-muted-foreground">This will invalidate your current key.</p>
                  </div>
                  <Button variant="outline" className="border-white/10 bg-white/[0.03] hover:bg-white/[0.07]">
                    <RefreshCw data-icon="inline-start" />
                    Regenerate
                  </Button>
                </div>
              </Panel>

              <Panel title="Rate Limits" description="Current API capacity">
                <div className="grid gap-3">
                  <MetricTile value="1,000" label="Requests/minute" />
                  <MetricTile value="100K" label="Tokens/minute" />
                  <MetricTile value="10MB" label="Max file size" />
                </div>
              </Panel>

              <Panel title="Webhooks" description="Event streams for connected systems" className="lg:col-span-2">
                <div className="grid gap-4 lg:grid-cols-[1fr_0.8fr]">
                  <div className="space-y-2">
                    <Label htmlFor="webhookUrl">Webhook URL</Label>
                    <Input id="webhookUrl" type="url" placeholder="https://your-domain.com/webhook" />
                  </div>
                  <div className="grid gap-2">
                    {["message.created", "chat.completed", "error.occurred"].map((event) => (
                      <div key={event} className="flex items-center gap-3 rounded-lg bg-white/[0.03] px-3 py-2 ring-1 ring-white/5">
                        <Switch id={event} />
                        <Label htmlFor={event} className="font-mono text-sm">{event}</Label>
                      </div>
                    ))}
                  </div>
                </div>
              </Panel>
            </motion.div>
          </TabsContent>

          <TabsContent value="billing">
            <motion.div {...fadeIn} className="grid gap-5 lg:grid-cols-[1fr_1fr]">
              <Panel title="Current Plan" description="Subscription and payment controls">
                <div className="flex flex-col justify-between gap-4 rounded-lg border border-primary/20 bg-primary/10 p-4 sm:flex-row sm:items-center">
                  <div className="flex items-center gap-4">
                    <div className="flex size-12 items-center justify-center rounded-lg bg-primary/15 ring-1 ring-primary/25">
                      <Zap className="size-6 text-primary" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-lg font-semibold">Pro Plan</p>
                        <Badge>Current</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">$20/month, billed monthly</p>
                    </div>
                  </div>
                  <Button variant="outline" className="border-white/10 bg-white/[0.03] hover:bg-white/[0.07]">Change Plan</Button>
                </div>

                <div className="grid gap-3 text-sm">
                  <div className="flex items-center justify-between"><span className="text-muted-foreground">Next billing date</span><span>June 15, 2026</span></div>
                  <div className="flex items-center justify-between"><span className="text-muted-foreground">Payment method</span><span>Visa ending in 4242</span></div>
                </div>
              </Panel>

              <Panel title="Usage This Month" description="Capacity and utilization">
                {[
                  { label: "Messages", value: "12,847 sent", percent: "33%", color: "bg-primary" },
                  { label: "API Calls", value: "45,200 / 100,000", percent: "45%", color: "bg-cyan-300" },
                  { label: "Storage", value: "2.4 GB / 10 GB", percent: "24%", color: "bg-emerald-300" },
                ].map((item) => (
                  <div key={item.label} className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span>{item.label}</span>
                      <span className="text-muted-foreground">{item.value}</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
                      <div className={`h-full rounded-full ${item.color}`} style={{ width: item.percent }} />
                    </div>
                  </div>
                ))}
              </Panel>

              <Panel title="Billing History" description="Past invoices and receipts" className="lg:col-span-2">
                <div className="divide-y divide-white/10 overflow-hidden rounded-lg border border-white/10">
                  {[
                    { date: "May 15, 2026", amount: "$20.00", status: "Paid" },
                    { date: "Apr 15, 2026", amount: "$20.00", status: "Paid" },
                    { date: "Mar 15, 2026", amount: "$20.00", status: "Paid" },
                  ].map((invoice) => (
                    <div key={invoice.date} className="grid gap-3 bg-white/[0.025] p-3 sm:grid-cols-[1fr_auto] sm:items-center">
                      <div>
                        <p className="font-medium">{invoice.date}</p>
                        <p className="text-sm text-muted-foreground">Pro Plan - Monthly</p>
                      </div>
                      <div className="flex flex-wrap items-center gap-3">
                        <Badge variant="secondary" className="bg-success/10 text-success">{invoice.status}</Badge>
                        <span className="font-medium">{invoice.amount}</span>
                        <Button variant="ghost" size="sm">
                          <Download data-icon="inline-start" />
                          Download
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </Panel>

              <Panel title="Account Boundary" description="Destructive subscription and account actions" className="border-destructive/40 lg:col-span-2">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="flex items-center justify-between gap-4 rounded-lg bg-white/[0.03] p-3 ring-1 ring-white/5">
                    <div>
                      <p className="font-medium">Cancel Subscription</p>
                      <p className="text-sm text-muted-foreground">Downgrade at end of billing cycle.</p>
                    </div>
                    <Button variant="outline">Cancel</Button>
                  </div>
                  <div className="flex items-center justify-between gap-4 rounded-lg bg-destructive/10 p-3 ring-1 ring-destructive/20">
                    <div>
                      <p className="font-medium">Delete Account</p>
                      <p className="text-sm text-muted-foreground">Permanently remove all workspace data.</p>
                    </div>
                    <Button variant="destructive">Delete</Button>
                  </div>
                </div>
              </Panel>
            </motion.div>
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}
