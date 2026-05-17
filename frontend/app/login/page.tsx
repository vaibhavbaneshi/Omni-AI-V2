"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import { Sparkles, Mail, Lock, ArrowRight, Github, Chrome } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Checkbox } from "@/components/ui/checkbox";
import { fadeUpVariant } from "@/lib/motion";

export default function LoginPage() {
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    // Simulate login - replace with actual auth
    await new Promise(resolve => setTimeout(resolve, 1000));
    router.push("/chat");
  };

  return (
    <div className="min-h-screen flex items-center justify-center p-4 relative overflow-hidden bg-[#050505]">
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
            <h1 className="text-2xl font-bold tracking-tight mb-2 text-foreground">Welcome back</h1>
            <p className="text-[13px] text-muted-foreground/80">
              Sign in to your intelligent workspace
            </p>
          </div>

          {/* Social Login Buttons */}
          <div className="grid grid-cols-2 gap-3 mb-6">
            <Button variant="outline" className="w-full bg-white/[0.02] border-white/5 hover:bg-white/5 hover:text-foreground transition-colors text-[13px] h-9" disabled={isLoading}>
              <Github className="size-4 mr-2 opacity-70" />
              GitHub
            </Button>
            <Button variant="outline" className="w-full bg-white/[0.02] border-white/5 hover:bg-white/5 hover:text-foreground transition-colors text-[13px] h-9" disabled={isLoading}>
              <Chrome className="size-4 mr-2 opacity-70" />
              Google
            </Button>
          </div>

          <div className="relative mb-6">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t border-white/5" />
            </div>
            <div className="relative flex justify-center text-[11px] uppercase tracking-wider">
              <span className="bg-[#0A0A0A] px-2 text-muted-foreground/50">
                Or continue with email
              </span>
            </div>
          </div>

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email" className="text-[12px] text-muted-foreground/80">Email</Label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground/50" />
                <Input 
                  id="email"
                  type="email" 
                  placeholder="you@example.com"
                  className="pl-9 h-10 bg-white/[0.02] border-white/5 focus-visible:ring-1 focus-visible:ring-primary/30 focus-visible:border-primary/30 text-[13px] placeholder:text-muted-foreground/30 shadow-inner transition-all"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="password" className="text-[12px] text-muted-foreground/80">Password</Label>
                <Link 
                  href="/forgot-password" 
                  className="text-[11px] text-primary/80 hover:text-primary hover:underline transition-colors"
                >
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 size-4 text-muted-foreground/50" />
                <Input 
                  id="password"
                  type="password" 
                  placeholder="••••••••"
                  className="pl-9 h-10 bg-white/[0.02] border-white/5 focus-visible:ring-1 focus-visible:ring-primary/30 focus-visible:border-primary/30 text-[13px] placeholder:text-muted-foreground/30 shadow-inner transition-all"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  disabled={isLoading}
                />
              </div>
            </div>

            <div className="flex items-center gap-2 pt-1 pb-2">
              <Checkbox id="remember" className="border-white/10 data-[state=checked]:bg-primary" />
              <Label htmlFor="remember" className="text-[12px] text-muted-foreground/70 font-normal cursor-pointer">
                Remember me for 30 days
              </Label>
            </div>

            <Button type="submit" className="w-full h-10 bg-primary text-primary-foreground hover:bg-primary/90 glow-primary transition-all text-[13px] font-medium" disabled={isLoading}>
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="size-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin" />
                  Signing in...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2 w-full">
                  Sign In
                  <ArrowRight className="size-4" />
                </span>
              )}
            </Button>
          </form>

          <p className="mt-6 text-center text-[12px] text-muted-foreground/60">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-primary hover:underline font-medium">
              Create one
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  );
}
