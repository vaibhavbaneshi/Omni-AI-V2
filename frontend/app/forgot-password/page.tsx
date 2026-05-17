"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, Mail, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export default function ForgotPasswordPage() {
  const [sent, setSent] = useState(false);

  return (
    <main className="flex min-h-dvh items-center justify-center overflow-x-hidden bg-[#050505] p-4 py-8">
      <div className="w-full max-w-[400px] rounded-3xl border border-white/5 bg-white/[0.02] p-8 shadow-premium backdrop-blur-2xl">
        <Link href="/" className="mx-auto mb-8 flex size-10 items-center justify-center rounded-xl border border-primary/20 bg-primary/10">
          <Sparkles className="size-5 text-primary" />
        </Link>
        <div className="mb-8 text-center">
          <h1 className="mb-2 text-2xl font-bold tracking-tight">Reset password</h1>
          <p className="text-[13px] text-muted-foreground/80">Enter your email and we will send reset instructions.</p>
        </div>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            setSent(true);
          }}
        >
          <div className="space-y-2">
            <Label htmlFor="email" className="text-[12px] text-muted-foreground/80">Email</Label>
            <div className="relative">
              <Mail className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground/50" />
              <Input id="email" type="email" required placeholder="you@example.com" className="h-10 border-white/5 bg-white/[0.02] pl-9 text-[13px]" />
            </div>
          </div>
          <Button type="submit" className="h-10 w-full glow-primary">Send Reset Link</Button>
        </form>
        {sent && (
          <p className="mt-4 rounded-lg border border-success/20 bg-success/10 px-3 py-2 text-center text-sm text-success">
            Reset instructions are ready to send once your backend email service is connected.
          </p>
        )}
        <Button variant="ghost" className="mt-4 w-full text-muted-foreground" asChild>
          <Link href="/login">
            <ArrowLeft data-icon="inline-start" />
            Back to sign in
          </Link>
        </Button>
      </div>
    </main>
  );
}
