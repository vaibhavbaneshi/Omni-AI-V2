"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Button, buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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
import { useModels } from "@/hooks/useModels";
import {
  ApiError,
  cancelWorkspaceSubscription,
  changeWorkspaceBillingPlan,
  changeWorkspacePassword,
  deleteWorkspaceAccount,
  disableTwoFactor,
  downloadWorkspaceInvoice,
  enableTwoFactor,
  getWorkspaceSettings,
  regenerateWorkspaceApiKey,
  revokeOtherWorkspaceSessions,
  revokeWorkspaceSession,
  setupTwoFactor,
  updateWorkspacePreferences,
  updateWorkspaceProfile,
  updateWorkspaceWebhook,
  uploadWorkspaceAvatar,
  type WorkspaceSettings,
} from "@/lib/api";
import { clearSession, createSession, getInitials, useRequireAuth } from "@/lib/auth";
import { setPreferredModelId } from "@/lib/model-preferences";

const fadeIn = { initial: { opacity: 0, y: 16 }, animate: { opacity: 1, y: 0 } };
const WEBHOOK_EVENTS = ["message.created", "chat.completed", "error.occurred"] as const;

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

function MetricTile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-white/[0.035] p-4 ring-1 ring-white/5">
      <p className="text-2xl font-semibold">{value}</p>
      <p className="mt-1 text-sm text-muted-foreground">{label}</p>
    </div>
  );
}

function formatRelativeDate(value?: string | null) {
  if (!value) return "Never";
  const date = new Date(value);
  const days = Math.floor((Date.now() - date.getTime()) / (1000 * 60 * 60 * 24));
  if (days <= 0) return "Today";
  if (days === 1) return "1 day ago";
  return `${days} days ago`;
}

function formatBytes(bytes: number) {
  if (bytes >= 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(0)}MB`;
  return `${Math.round(bytes / 1024)}KB`;
}

export default function SettingsPage() {
  const router = useRouter();
  const { session, ready, authenticated } = useRequireAuth();
  const { models } = useModels();
  const avatarInputRef = useRef<HTMLInputElement>(null);

  const [settings, setSettings] = useState<WorkspaceSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [email, setEmail] = useState("");
  const [bio, setBio] = useState("");
  const [preferences, setPreferences] = useState<WorkspaceSettings["preferences"] | null>(null);
  const [webhookUrl, setWebhookUrl] = useState("");
  const [webhookEvents, setWebhookEvents] = useState<Record<string, boolean>>({});
  const [webhookEnabled, setWebhookEnabled] = useState(false);

  const [showApiKey, setShowApiKey] = useState(false);
  const [copiedKey, setCopiedKey] = useState(false);
  const [revealedApiKey, setRevealedApiKey] = useState<string | null>(null);

  const [passwordOpen, setPasswordOpen] = useState(false);
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");

  const [sessionsOpen, setSessionsOpen] = useState(false);
  const [twoFactorOpen, setTwoFactorOpen] = useState(false);
  const [twoFactorSecret, setTwoFactorSecret] = useState("");
  const [twoFactorUri, setTwoFactorUri] = useState("");
  const [twoFactorCode, setTwoFactorCode] = useState("");
  const [disablePassword, setDisablePassword] = useState("");

  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleteConfirmation, setDeleteConfirmation] = useState("");

  const applySettings = useCallback((payload: WorkspaceSettings) => {
    setSettings(payload);
    setFirstName(payload.profile.first_name);
    setLastName(payload.profile.last_name);
    setEmail(payload.profile.email);
    setBio(payload.profile.bio);
    setPreferences(payload.preferences);
    setWebhookUrl(payload.api.webhook.url);
    setWebhookEnabled(payload.api.webhook.enabled);
    setWebhookEvents(
      Object.fromEntries(WEBHOOK_EVENTS.map((event) => [event, payload.api.webhook.events.includes(event)]))
    );
    setPreferredModelId(payload.preferences.default_model);
    document.documentElement.dataset.theme = payload.preferences.theme;
    document.documentElement.dataset.fontSize = payload.preferences.font_size;
    document.documentElement.dataset.compact = payload.preferences.compact_mode ? "true" : "false";
  }, []);

  const refreshSettings = useCallback(async () => {
    if (!session?.token) return;
    const payload = await getWorkspaceSettings(session.token);
    applySettings(payload);
  }, [applySettings, session?.token]);

  useEffect(() => {
    if (!ready || !authenticated || !session?.token) return;
    let cancelled = false;
    setLoading(true);
    getWorkspaceSettings(session.token)
      .then((payload) => {
        if (!cancelled) applySettings(payload);
      })
      .catch((error) => {
        if (!cancelled) {
          setErrorMessage(error instanceof Error ? error.message : "Failed to load settings.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [applySettings, authenticated, ready, session?.token]);

  const handleSave = async () => {
    if (!session?.token || !preferences) return;
    setIsSaving(true);
    setErrorMessage(null);
    setStatusMessage(null);
    try {
      const [profile] = await Promise.all([
        updateWorkspaceProfile(
          { first_name: firstName, last_name: lastName, email, bio },
          session.token
        ),
        updateWorkspacePreferences(preferences, session.token),
        updateWorkspaceWebhook(
          {
            url: webhookUrl,
            events: WEBHOOK_EVENTS.filter((event) => webhookEvents[event]),
            enabled: webhookEnabled,
          },
          session.token
        ),
      ]);

      createSession({
        token: session.token,
        email: profile.email,
        username: profile.username,
        name: `${profile.first_name} ${profile.last_name}`.trim() || profile.display_name,
      });

      setPreferredModelId(preferences.default_model);
      await refreshSettings();
      setStatusMessage("Settings saved.");
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "Failed to save settings.");
    } finally {
      setIsSaving(false);
    }
  };

  const handleAvatarChange = async (file: File) => {
    if (!session?.token) return;
    try {
      const result = await uploadWorkspaceAvatar(file, session.token);
      await refreshSettings();
      setStatusMessage("Avatar updated.");
      if (result.avatar_url) {
        createSession({
          token: session.token,
          email,
          username: session.username,
          name: `${firstName} ${lastName}`.trim() || session.name,
        });
      }
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "Avatar upload failed.");
    }
  };

  const handlePasswordChange = async () => {
    if (!session?.token) return;
    try {
      await changeWorkspacePassword(
        {
          current_password: settings?.profile.has_password ? currentPassword : undefined,
          new_password: newPassword,
          confirm_password: confirmPassword,
        },
        session.token
      );
      setPasswordOpen(false);
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      await refreshSettings();
      setStatusMessage("Password updated.");
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "Password update failed.");
    }
  };

  const handleTwoFactorToggle = async (enabled: boolean) => {
    if (!session?.token) return;
    if (enabled) {
      try {
        const setup = await setupTwoFactor(session.token);
        setTwoFactorSecret(setup.secret);
        setTwoFactorUri(setup.provisioning_uri);
        setTwoFactorCode("");
        setTwoFactorOpen(true);
      } catch (error) {
        setErrorMessage(error instanceof ApiError ? error.message : "Failed to start 2FA setup.");
      }
      return;
    }

    setTwoFactorCode("");
    setDisablePassword("");
    setTwoFactorOpen(true);
  };

  const handleEnableTwoFactor = async () => {
    if (!session?.token) return;
    try {
      await enableTwoFactor(twoFactorCode, session.token);
      setTwoFactorOpen(false);
      await refreshSettings();
      setStatusMessage("Two-factor authentication enabled.");
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "Invalid authentication code.");
    }
  };

  const handleDisableTwoFactor = async () => {
    if (!session?.token) return;
    try {
      await disableTwoFactor(
        { code: twoFactorCode, password: disablePassword || undefined },
        session.token
      );
      setTwoFactorOpen(false);
      await refreshSettings();
      setStatusMessage("Two-factor authentication disabled.");
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "Failed to disable 2FA.");
    }
  };

  const handleRegenerateApiKey = async () => {
    if (!session?.token) return;
    try {
      const result = await regenerateWorkspaceApiKey(session.token);
      setRevealedApiKey(result.api_key);
      await refreshSettings();
      setStatusMessage(result.message);
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "Failed to regenerate API key.");
    }
  };

  const handleCopyKey = async () => {
    const value = revealedApiKey || settings?.api.key.prefix;
    if (!value) return;
    await navigator.clipboard.writeText(value);
    setCopiedKey(true);
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const handlePlanChange = async (plan: "free" | "pro") => {
    if (!session?.token) return;
    try {
      const billing = await changeWorkspaceBillingPlan(plan, session.token);
      setSettings((current) => (current ? { ...current, billing } : current));
      setStatusMessage(plan === "pro" ? "Upgraded to Pro plan." : "Switched to Free plan.");
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "Plan change failed.");
    }
  };

  const handleCancelSubscription = async () => {
    if (!session?.token) return;
    try {
      await cancelWorkspaceSubscription(session.token);
      await refreshSettings();
      setStatusMessage("Subscription will cancel at period end.");
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "Cancellation failed.");
    }
  };

  const handleDownloadInvoice = async (invoiceId: number) => {
    if (!session?.token) return;
    try {
      const content = await downloadWorkspaceInvoice(invoiceId, session.token);
      const blob = new Blob([content], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `invoice-${invoiceId}.txt`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "Download failed.");
    }
  };

  const handleDeleteAccount = async () => {
    if (!session?.token) return;
    try {
      await deleteWorkspaceAccount(deleteConfirmation, session.token);
      clearSession();
      router.replace("/login");
    } catch (error) {
      setErrorMessage(error instanceof ApiError ? error.message : "Account deletion failed.");
    }
  };

  if (!ready || !authenticated || loading || !settings || !preferences) {
    return <div className="min-h-screen bg-background" />;
  }

  const initials = getInitials(`${firstName} ${lastName}`.trim() || settings.profile.display_name);
  const activeSessions = settings.security.sessions.length;
  const apiKeyDisplay = revealedApiKey || settings.api.key.prefix || "No key generated";
  const billing = settings.billing;

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
        {(statusMessage || errorMessage) && (
          <div
            className={`rounded-lg border px-4 py-3 text-sm ${
              errorMessage
                ? "border-destructive/30 bg-destructive/10 text-destructive"
                : "border-emerald-400/20 bg-emerald-400/10 text-emerald-200"
            }`}
          >
            {errorMessage || statusMessage}
          </div>
        )}

        <motion.section {...fadeIn} className="grid gap-4 rounded-lg border border-white/10 bg-card/70 p-4 shadow-premium backdrop-blur-xl sm:p-6 lg:grid-cols-[1fr_auto]">
          <div className="max-w-3xl space-y-3">
            <Badge className="bg-primary/15 text-primary hover:bg-primary/20">System configuration</Badge>
            <h1 className="text-3xl font-semibold leading-tight sm:text-4xl">
              Tune the behavior, access, and economics of your AI workspace.
            </h1>
          </div>
          <div className="grid gap-3 sm:grid-cols-3 lg:w-[420px] lg:grid-cols-1">
            <div className="flex items-center gap-3 rounded-lg bg-white/[0.035] p-3 ring-1 ring-white/5">
              <Brain className="size-4 text-primary" />
              <div>
                <p className="text-xs text-muted-foreground">Model routing</p>
                <p className="text-sm font-medium">{preferences.default_model}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg bg-white/[0.035] p-3 ring-1 ring-white/5">
              <SlidersHorizontal className="size-4 text-primary" />
              <div>
                <p className="text-xs text-muted-foreground">Workspace mode</p>
                <p className="text-sm font-medium capitalize">{preferences.response_style}</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg bg-white/[0.035] p-3 ring-1 ring-white/5">
              <Shield className="size-4 text-primary" />
              <div>
                <p className="text-xs text-muted-foreground">Security posture</p>
                <p className="text-sm font-medium">
                  {settings.security.totp_enabled ? "2FA enabled" : "Protected"}
                </p>
              </div>
            </div>
          </div>
        </motion.section>

        <Tabs defaultValue="profile" className="gap-5">
          <TabsList className="grid h-auto w-full grid-cols-2 gap-1 rounded-lg border border-white/10 bg-card/70 p-1 shadow-premium sm:grid-cols-4 lg:w-fit">
            <TabsTrigger value="profile" className="h-10 gap-2 rounded-lg px-3"><User className="size-4" /><span>Profile</span></TabsTrigger>
            <TabsTrigger value="preferences" className="h-10 gap-2 rounded-lg px-3"><Palette className="size-4" /><span>AI Controls</span></TabsTrigger>
            <TabsTrigger value="api" className="h-10 gap-2 rounded-lg px-3"><Key className="size-4" /><span>API</span></TabsTrigger>
            <TabsTrigger value="billing" className="h-10 gap-2 rounded-lg px-3"><CreditCard className="size-4" /><span>Billing</span></TabsTrigger>
          </TabsList>

          <TabsContent value="profile">
            <motion.div {...fadeIn} className="grid gap-5 lg:grid-cols-[1.25fr_0.75fr]">
              <Panel title="Identity" description="Account details and workspace presence">
                <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
                  <Avatar className="size-20 ring-1 ring-white/10">
                    {settings.profile.avatar_url ? (
                      <AvatarImage src={settings.profile.avatar_url} alt={settings.profile.display_name} />
                    ) : null}
                    <AvatarFallback className="bg-primary/15 text-2xl text-primary">{initials}</AvatarFallback>
                  </Avatar>
                  <div className="space-y-2">
                    <input
                      ref={avatarInputRef}
                      type="file"
                      accept="image/*"
                      className="hidden"
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (file) void handleAvatarChange(file);
                      }}
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      className="border-white/10 bg-white/[0.03] hover:bg-white/[0.07]"
                      onClick={() => avatarInputRef.current?.click()}
                    >
                      Change Avatar
                    </Button>
                    <p className="text-xs text-muted-foreground">JPG, PNG or GIF. Max 2MB.</p>
                  </div>
                </div>
                <Separator />
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="space-y-2"><Label htmlFor="firstName">First Name</Label><Input id="firstName" value={firstName} onChange={(e) => setFirstName(e.target.value)} /></div>
                  <div className="space-y-2"><Label htmlFor="lastName">Last Name</Label><Input id="lastName" value={lastName} onChange={(e) => setLastName(e.target.value)} /></div>
                  <div className="space-y-2 sm:col-span-2"><Label htmlFor="email">Email</Label><Input id="email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} /></div>
                  <div className="space-y-2 sm:col-span-2"><Label htmlFor="bio">Operator Notes</Label><Textarea id="bio" value={bio} onChange={(e) => setBio(e.target.value)} className="min-h-24 resize-none" /></div>
                </div>
              </Panel>

              <Panel title="Security" description="Protection and signed-in devices">
                <div className="flex items-center justify-between gap-4 rounded-lg bg-white/[0.03] p-3 ring-1 ring-white/5">
                  <div className="space-y-0.5">
                    <Label className="text-sm">Two-Factor Authentication</Label>
                    <p className="text-sm text-muted-foreground">Require a second factor for sensitive changes</p>
                  </div>
                  <Switch checked={settings.security.totp_enabled} onCheckedChange={(checked) => void handleTwoFactorToggle(Boolean(checked))} />
                </div>
                <div className="flex items-center justify-between gap-4 rounded-lg bg-white/[0.03] p-3 ring-1 ring-white/5">
                  <div className="flex items-center gap-3">
                    <Lock className="size-4 text-primary" />
                    <div>
                      <p className="font-medium">{settings.profile.has_password ? "Password" : "Set Password"}</p>
                      <p className="text-sm text-muted-foreground">
                        {settings.profile.has_password
                          ? `Last changed ${formatRelativeDate(settings.profile.password_changed_at)}`
                          : settings.profile.oauth_provider
                          ? `Signed in with ${settings.profile.oauth_provider}`
                          : "No password set"}
                      </p>
                    </div>
                  </div>
                  <Button variant="outline" size="sm" className="border-white/10 bg-white/[0.03] hover:bg-white/[0.07]" onClick={() => setPasswordOpen(true)}>
                    {settings.profile.has_password ? "Change" : "Set"}
                  </Button>
                </div>
                <div className="flex items-center justify-between gap-4 rounded-lg bg-white/[0.03] p-3 ring-1 ring-white/5">
                  <div>
                    <p className="font-medium">Active Sessions</p>
                    <p className="text-sm text-muted-foreground">{activeSessions} device(s) currently signed in</p>
                  </div>
                  <Button variant="outline" size="sm" className="border-white/10 bg-white/[0.03] hover:bg-white/[0.07]" onClick={() => setSessionsOpen(true)}>
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
                    <Select value={preferences.default_model} onValueChange={(value) => value && setPreferences({ ...preferences, default_model: value })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent><SelectGroup>{models.map((model) => (<SelectItem key={model.id} value={model.id}>{model.name}</SelectItem>))}</SelectGroup></SelectContent>
                    </Select>
                  </div>
                  <div className="space-y-2">
                    <Label>Response Style</Label>
                    <Select value={preferences.response_style} onValueChange={(value) => value && setPreferences({ ...preferences, response_style: value })}>
                      <SelectTrigger><SelectValue /></SelectTrigger>
                      <SelectContent><SelectGroup>{["concise", "balanced", "detailed"].map((style) => (<SelectItem key={style} value={style}>{style}</SelectItem>))}</SelectGroup></SelectContent>
                    </Select>
                  </div>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="systemPrompt">Custom System Prompt</Label>
                  <Textarea id="systemPrompt" value={preferences.system_prompt} onChange={(e) => setPreferences({ ...preferences, system_prompt: e.target.value })} className="min-h-32 resize-none" />
                </div>
                <div className="grid gap-3">
                  {[
                    ["web_search_enabled", "Web Search", "Enable real-time web context in responses"],
                    ["code_execution_enabled", "Code Execution", "Allow AI to run controlled code snippets"],
                    ["streaming_enabled", "Streaming Responses", "Show responses as they are generated"],
                  ].map(([key, title, description]) => (
                    <div key={key} className="flex items-center justify-between gap-4 rounded-lg bg-white/[0.03] p-3 ring-1 ring-white/5">
                      <div className="space-y-0.5"><Label className="text-sm">{title}</Label><p className="text-sm text-muted-foreground">{description}</p></div>
                      <Switch checked={preferences[key as keyof typeof preferences] as boolean} onCheckedChange={(checked) => setPreferences({ ...preferences, [key]: Boolean(checked) })} />
                    </div>
                  ))}
                </div>
              </Panel>
              <div className="grid gap-5">
                <Panel title="Appearance" description="Workspace density and display preferences">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label>Theme</Label>
                      <Select value={preferences.theme} onValueChange={(value) => value && setPreferences({ ...preferences, theme: value })}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent><SelectGroup>{["light", "dark", "system"].map((theme) => (<SelectItem key={theme} value={theme}>{theme}</SelectItem>))}</SelectGroup></SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Font Size</Label>
                      <Select value={preferences.font_size} onValueChange={(value) => value && setPreferences({ ...preferences, font_size: value })}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent><SelectGroup>{["small", "medium", "large"].map((size) => (<SelectItem key={size} value={size}>{size}</SelectItem>))}</SelectGroup></SelectContent>
                      </Select>
                    </div>
                  </div>
                  <div className="flex items-center justify-between gap-4 rounded-lg bg-white/[0.03] p-3 ring-1 ring-white/5">
                    <div className="space-y-0.5"><Label className="text-sm">Compact Mode</Label><p className="text-sm text-muted-foreground">Reduce spacing in repeated chat surfaces</p></div>
                    <Switch checked={preferences.compact_mode} onCheckedChange={(checked) => setPreferences({ ...preferences, compact_mode: Boolean(checked) })} />
                  </div>
                </Panel>
                <Panel title="Notifications" description="Operational alerts and product updates">
                  {[
                    ["email_notifications", "Email Notifications", "Receive account and workflow updates"],
                    ["product_updates", "Product Updates", "News about new features and improvements"],
                    ["usage_alerts", "Usage Alerts", "Warn when approaching limits"],
                  ].map(([key, title, description]) => (
                    <div key={key} className="flex items-center justify-between gap-4 rounded-lg bg-white/[0.03] p-3 ring-1 ring-white/5">
                      <div className="space-y-0.5"><Label className="text-sm">{title}</Label><p className="text-sm text-muted-foreground">{description}</p></div>
                      <Switch checked={preferences[key as keyof typeof preferences] as boolean} onCheckedChange={(checked) => setPreferences({ ...preferences, [key]: Boolean(checked) })} />
                    </div>
                  ))}
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
                      <p className="text-sm text-muted-foreground">
                        {settings.api.key.created_at ? `Created ${formatRelativeDate(settings.api.key.created_at)}` : "Not generated yet"}
                      </p>
                    </div>
                    <Badge className="bg-emerald-400/10 text-emerald-200 hover:bg-emerald-400/15">{settings.api.key.active ? "Active" : "Inactive"}</Badge>
                  </div>
                  <div className="relative">
                    <Input type={showApiKey ? "text" : "password"} value={apiKeyDisplay} readOnly className="pr-20 font-mono text-sm" />
                    <div className="absolute right-2 top-1/2 flex -translate-y-1/2 items-center gap-1">
                      <Button variant="ghost" size="icon" className="size-7" onClick={() => setShowApiKey(!showApiKey)} aria-label="Toggle API key visibility">
                        {showApiKey ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
                      </Button>
                      <Button variant="ghost" size="icon" className="size-7" onClick={() => void handleCopyKey()} aria-label="Copy API key">
                        {copiedKey ? <Check className="size-4 text-success" /> : <Copy className="size-4" />}
                      </Button>
                    </div>
                  </div>
                </div>
                <div className="flex flex-col justify-between gap-4 rounded-lg bg-white/[0.03] p-3 ring-1 ring-white/5 sm:flex-row sm:items-center">
                  <div><p className="font-medium">Generate New Key</p><p className="text-sm text-muted-foreground">This will invalidate your current key.</p></div>
                  <Button variant="outline" className="border-white/10 bg-white/[0.03] hover:bg-white/[0.07]" onClick={() => void handleRegenerateApiKey()}>
                    <RefreshCw data-icon="inline-start" />Regenerate
                  </Button>
                </div>
              </Panel>
              <Panel title="Rate Limits" description="Current API capacity">
                <div className="grid gap-3">
                  <MetricTile value={String(settings.api.rate_limits.requests_per_minute)} label="Requests/minute" />
                  <MetricTile value={`${Math.round(settings.api.rate_limits.tokens_per_minute / 1000)}K`} label="Tokens/minute" />
                  <MetricTile value={formatBytes(settings.api.rate_limits.max_upload_bytes)} label="Max file size" />
                </div>
              </Panel>
              <Panel title="Webhooks" description="Event streams for connected systems" className="lg:col-span-2">
                <div className="grid gap-4 lg:grid-cols-[1fr_0.8fr]">
                  <div className="space-y-2">
                    <Label htmlFor="webhookUrl">Webhook URL</Label>
                    <Input id="webhookUrl" type="url" value={webhookUrl} onChange={(e) => setWebhookUrl(e.target.value)} placeholder="https://your-domain.com/webhook" />
                    <div className="flex items-center gap-3 pt-2">
                      <Switch checked={webhookEnabled} onCheckedChange={setWebhookEnabled} id="webhook-enabled" />
                      <Label htmlFor="webhook-enabled">Enable webhook delivery</Label>
                    </div>
                  </div>
                  <div className="grid gap-2">
                    {WEBHOOK_EVENTS.map((event) => (
                      <div key={event} className="flex items-center gap-3 rounded-lg bg-white/[0.03] px-3 py-2 ring-1 ring-white/5">
                        <Switch id={event} checked={Boolean(webhookEvents[event])} onCheckedChange={(checked) => setWebhookEvents({ ...webhookEvents, [event]: Boolean(checked) })} />
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
                    <div className="flex size-12 items-center justify-center rounded-lg bg-primary/15 ring-1 ring-primary/25"><Zap className="size-6 text-primary" /></div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="text-lg font-semibold capitalize">{billing.plan} Plan</p>
                        <Badge>{billing.cancel_at_period_end ? "Cancelling" : "Current"}</Badge>
                      </div>
                      <p className="text-sm text-muted-foreground">
                        ${(billing.amount_cents / 100).toFixed(2)}/{billing.billing_cycle === "monthly" ? "month" : billing.billing_cycle}
                      </p>
                    </div>
                  </div>
                  <Button variant="outline" className="border-white/10 bg-white/[0.03] hover:bg-white/[0.07]" onClick={() => void handlePlanChange(billing.plan === "pro" ? "free" : "pro")}>
                    {billing.plan === "pro" ? "Downgrade" : "Upgrade to Pro"}
                  </Button>
                </div>
                <div className="grid gap-3 text-sm">
                  <div className="flex items-center justify-between"><span className="text-muted-foreground">Next billing date</span><span>{billing.next_billing_date ? new Date(billing.next_billing_date).toLocaleDateString() : "—"}</span></div>
                  <div className="flex items-center justify-between"><span className="text-muted-foreground">Payment method</span><span>{billing.payment_method_brand && billing.payment_method_last4 ? `${billing.payment_method_brand} ending in ${billing.payment_method_last4}` : "None on file"}</span></div>
                </div>
              </Panel>
              <Panel title="Usage This Month" description="Capacity and utilization">
                {[
                  { label: "Messages", item: billing.usage.messages },
                  { label: "API Calls", item: billing.usage.api_calls },
                  { label: "Storage", item: billing.usage.storage_gb, suffix: "GB" },
                ].map(({ label, item, suffix = "" }) => (
                  <div key={label} className="space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span>{label}</span>
                      <span className="text-muted-foreground">{item.used}{suffix} / {item.limit}{suffix}</span>
                    </div>
                    <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
                      <div className="h-full rounded-full bg-primary" style={{ width: `${item.percent}%` }} />
                    </div>
                  </div>
                ))}
              </Panel>
              <Panel title="Billing History" description="Past invoices and receipts" className="lg:col-span-2">
                <div className="divide-y divide-white/10 overflow-hidden rounded-lg border border-white/10">
                  {billing.invoices.length === 0 ? (
                    <p className="p-4 text-sm text-muted-foreground">No invoices yet.</p>
                  ) : (
                    billing.invoices.map((invoice) => (
                      <div key={invoice.id} className="grid gap-3 bg-white/[0.025] p-3 sm:grid-cols-[1fr_auto] sm:items-center">
                        <div><p className="font-medium">{invoice.date}</p><p className="text-sm text-muted-foreground">{invoice.description}</p></div>
                        <div className="flex flex-wrap items-center gap-3">
                          <Badge variant="secondary" className="bg-success/10 text-success">{invoice.status}</Badge>
                          <span className="font-medium">{invoice.amount}</span>
                          <Button variant="ghost" size="sm" onClick={() => void handleDownloadInvoice(invoice.id)}>
                            <Download data-icon="inline-start" />Download
                          </Button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </Panel>
              <Panel title="Account Boundary" description="Destructive subscription and account actions" className="border-destructive/40 lg:col-span-2">
                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="flex items-center justify-between gap-4 rounded-lg bg-white/[0.03] p-3 ring-1 ring-white/5">
                    <div><p className="font-medium">Cancel Subscription</p><p className="text-sm text-muted-foreground">Downgrade at end of billing cycle.</p></div>
                    <Button variant="outline" disabled={billing.plan === "free"} onClick={() => void handleCancelSubscription()}>Cancel</Button>
                  </div>
                  <div className="flex items-center justify-between gap-4 rounded-lg bg-destructive/10 p-3 ring-1 ring-destructive/20">
                    <div><p className="font-medium">Delete Account</p><p className="text-sm text-muted-foreground">Permanently remove all workspace data.</p></div>
                    <Button variant="destructive" onClick={() => setDeleteOpen(true)}>Delete</Button>
                  </div>
                </div>
              </Panel>
            </motion.div>
          </TabsContent>
        </Tabs>
      </main>

      <Dialog open={passwordOpen} onOpenChange={setPasswordOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{settings.profile.has_password ? "Change password" : "Set password"}</DialogTitle>
            <DialogDescription>Use at least 8 characters.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            {settings.profile.has_password && (
              <Input type="password" placeholder="Current password" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
            )}
            <Input type="password" placeholder="New password" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
            <Input type="password" placeholder="Confirm password" value={confirmPassword} onChange={(e) => setConfirmPassword(e.target.value)} />
          </div>
          <DialogFooter>
            <Button onClick={() => void handlePasswordChange()}>Save password</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={sessionsOpen} onOpenChange={setSessionsOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Active sessions</DialogTitle>
            <DialogDescription>Revoke access on devices you no longer use.</DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            {settings.security.sessions.map((item) => (
              <div key={item.id} className="flex items-center justify-between rounded-lg bg-white/[0.03] p-3 ring-1 ring-white/5">
                <div>
                  <p className="font-medium">{item.device_label}{item.is_current ? " (current)" : ""}</p>
                  <p className="text-xs text-muted-foreground">{item.ip_address || "Unknown IP"} · {formatRelativeDate(item.last_active_at)}</p>
                </div>
                {!item.is_current && (
                  <Button variant="outline" size="sm" onClick={async () => { await revokeWorkspaceSession(item.id, session?.token); await refreshSettings(); }}>
                    Revoke
                  </Button>
                )}
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={async () => { await revokeOtherWorkspaceSessions(session?.token); await refreshSettings(); }}>
              Sign out other devices
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={twoFactorOpen} onOpenChange={setTwoFactorOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{settings.security.totp_enabled ? "Disable 2FA" : "Enable 2FA"}</DialogTitle>
            <DialogDescription>
              {settings.security.totp_enabled
                ? "Enter your authenticator code to disable two-factor authentication."
                : "Add this secret to your authenticator app, then enter the 6-digit code."}
            </DialogDescription>
          </DialogHeader>
          {!settings.security.totp_enabled && twoFactorSecret && (
            <div className="space-y-2 rounded-lg bg-white/[0.03] p-3 text-sm ring-1 ring-white/5">
              <p className="font-mono break-all">{twoFactorSecret}</p>
              <p className="text-xs text-muted-foreground break-all">{twoFactorUri}</p>
            </div>
          )}
          <Input placeholder="Authentication code" value={twoFactorCode} onChange={(e) => setTwoFactorCode(e.target.value)} />
          {settings.security.totp_enabled && settings.profile.has_password && (
            <Input type="password" placeholder="Password" value={disablePassword} onChange={(e) => setDisablePassword(e.target.value)} />
          )}
          <DialogFooter>
            <Button onClick={() => void (settings.security.totp_enabled ? handleDisableTwoFactor() : handleEnableTwoFactor())}>
              {settings.security.totp_enabled ? "Disable 2FA" : "Verify and enable"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete account</DialogTitle>
            <DialogDescription>Type <strong>delete my account</strong> to confirm.</DialogDescription>
          </DialogHeader>
          <Input value={deleteConfirmation} onChange={(e) => setDeleteConfirmation(e.target.value)} placeholder="delete my account" />
          <DialogFooter>
            <Button variant="destructive" onClick={() => void handleDeleteAccount()}>Delete permanently</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
