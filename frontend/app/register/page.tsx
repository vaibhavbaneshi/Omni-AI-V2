"use client";

import { useState } from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import { Sparkles } from "lucide-react";
import { SocialAuthButtons } from "@/components/auth/social-auth-buttons";
import { useAuthRedirect } from "@/lib/auth";
import { fadeUpVariant } from "@/lib/motion";

export default function RegisterPage() {
  const { redirect } = useAuthRedirect("/dashboard");
  const [error, setError] = useState<string | null>(null);

  return (
    <div className="min-h-dvh flex items-center justify-center p-4 py-8 relative overflow-x-hidden bg-[#050505]">
      {/* Ambient Background */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,oklch(0.25_0.08_280),transparent_50%)] opacity-40" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_100%,oklch(0.2_0.06_200),transparent_50%)] opacity-30" />
        <div className="absolute inset-0 bg-[url('/noise.png')] opacity-[0.02] mix-blend-overlay" />
      </div>

      <motion.div 
        className="w-full max-w-[400px] relative z-10"
        variants={fadeUpVariant}
        initial="initial"
        animate="animate"
      >
        <div className="bg-white/[0.02] backdrop-blur-2xl border border-white/5 rounded-3xl p-8 shadow-premium">
          {/* Logo */}
          <div className="flex justify-center mb-8">
            <Link href="/" className="flex items-center gap-2">
              <div className="size-10 rounded-xl bg-primary/10 flex items-center justify-center border border-primary/20 shadow-[0_0_15px_rgba(var(--primary),0.15)]">
                <Sparkles className="size-5 text-primary" />
              </div>
            </Link>
          </div>

          <div className="text-center mb-8">
            <h1 className="text-2xl font-bold tracking-tight mb-2 text-foreground">Create account</h1>
            <p className="text-[13px] text-muted-foreground/80">
              Start building with Omni AI today
            </p>
          </div>

          {error && (
            <p className="mb-4 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-[12px] text-destructive">
              {error}
            </p>
          )}

          <SocialAuthButtons
            nextPath={redirect}
            onError={setError}
            onClearError={() => setError(null)}
          />

          <p className="mt-6 text-center text-[12px] text-muted-foreground/60">
            Already have an account?{" "}
            <Link href="/login" className="text-primary hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
