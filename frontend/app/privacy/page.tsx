import Link from "next/link";
import { Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function PrivacyPage() {
  return (
    <main className="min-h-screen overflow-x-hidden bg-background px-4 py-10 text-foreground sm:px-6">
      <div className="mx-auto max-w-3xl">
        <Link href="/" className="mb-10 flex w-fit items-center gap-2">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary/15 ring-1 ring-primary/25">
            <Sparkles className="size-5 text-primary" />
          </div>
          <span className="text-lg font-semibold">Omni AI</span>
        </Link>
        <div className="rounded-lg border border-white/10 bg-card/65 p-6 shadow-premium">
          <h1 className="text-3xl font-semibold">Privacy Policy</h1>
          <p className="mt-3 text-sm leading-6 text-muted-foreground">
            This demo frontend provides an illustrative privacy page so account and footer navigation resolve cleanly. Replace this content with your production privacy policy before launch.
          </p>
          <div className="mt-8 space-y-5 text-sm leading-6 text-muted-foreground">
            <p>Omni AI should only collect the account, usage, and workspace data required to provide the service.</p>
            <p>Production deployments should disclose model providers, retention periods, analytics, and user data controls.</p>
            <p>Security-sensitive settings and API keys should be handled by authenticated backend services, not only client state.</p>
          </div>
          <Button asChild className="mt-8">
            <Link href="/register">Create Account</Link>
          </Button>
        </div>
      </div>
    </main>
  );
}
