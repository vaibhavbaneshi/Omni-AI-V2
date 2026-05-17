"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { 
  Sparkles, 
  Brain, 
  FileText, 
  Code2, 
  ArrowRight,
  Check,
  Star,
  Globe,
  Layers,
  Lock,
  Terminal
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

// Premium motion easing
const premiumEasing = [0.16, 1, 0.3, 1] as const;

const fadeInUp = {
  initial: { opacity: 0, y: 30 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.8, ease: premiumEasing } }
};

const staggerContainer = {
  animate: {
    transition: {
      staggerChildren: 0.1
    }
  }
};

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-background text-foreground overflow-x-hidden selection:bg-primary/30">
      {/* Abstract Background Effects */}
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute inset-0 bg-[linear-gradient(to_right,#8080800a_1px,transparent_1px),linear-gradient(to_bottom,#8080800a_1px,transparent_1px)] bg-[size:24px_24px]"></div>
        <div className="absolute left-1/2 top-0 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[400px] bg-primary/20 rounded-full blur-[120px] opacity-50"></div>
      </div>

      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass border-b border-white/[0.05]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="size-8 rounded-lg bg-primary/20 flex items-center justify-center border border-primary/30 shadow-[0_0_15px_rgba(var(--primary),0.2)]">
                <Sparkles className="size-5 text-primary" />
              </div>
              <span className="text-xl font-semibold tracking-tight text-foreground">Omni AI</span>
            </div>
            
            <div className="hidden md:flex items-center gap-8">
              <Link href="#features" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Features
              </Link>
              <Link href="#pricing" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Pricing
              </Link>
              <Link href="#testimonials" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Testimonials
              </Link>
            </div>

            <div className="flex items-center gap-4">
              <Link href="/login" className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors">
                Sign In
              </Link>
              <Button size="sm" className="shadow-[0_0_20px_rgba(var(--primary),0.2)]" asChild>
                <Link href="/register">
                  Get Started
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-40 pb-24 z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div 
            className="text-center max-w-4xl mx-auto"
            initial="initial"
            animate="animate"
            variants={staggerContainer}
          >
            <motion.div variants={fadeInUp}>
              <Badge variant="outline" className="mb-8 border-primary/30 bg-primary/5 text-primary backdrop-blur-sm px-4 py-1.5 rounded-full text-xs font-medium">
                <Sparkles className="size-3.5 mr-2" />
                Omni AI 2.0 is now available
              </Badge>
            </motion.div>
            
            <motion.h1 
              variants={fadeInUp}
              className="text-5xl sm:text-6xl lg:text-7xl font-bold tracking-tight text-balance leading-tight"
            >
              Your Intelligent <br />
              <span className="text-gradient">AI Operating System</span>
            </motion.h1>
            
            <motion.p 
              variants={fadeInUp}
              className="mt-8 text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto text-pretty font-medium"
            >
              The most powerful AI workspace for developers and power users. 
              Chat with elite models, analyze complex documents, generate production code, and build faster.
            </motion.p>
            
            <motion.div 
              variants={fadeInUp}
              className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
            >
              <Button size="lg" className="w-full sm:w-auto glow-primary font-semibold text-primary-foreground h-12 px-8" asChild>
                <Link href="/register">
                  Start Building Free
                  <ArrowRight className="ml-2 size-4" />
                </Link>
              </Button>
              <Button variant="outline" size="lg" className="w-full sm:w-auto h-12 px-8 border-white/10 hover:bg-white/5" asChild>
                <Link href="/chat">
                  Try Live Demo
                </Link>
              </Button>
            </motion.div>
          </motion.div>

          {/* Hero Image/Preview Window */}
          <motion.div 
            className="mt-24 relative max-w-5xl mx-auto"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 1, ease: premiumEasing, delay: 0.2 }}
          >
            <div className="relative rounded-2xl border border-white/10 bg-[#0a0a0c]/80 backdrop-blur-xl shadow-premium overflow-hidden ring-1 ring-white/5">
              <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent pointer-events-none" />
              
              {/* macOS Style Window Chrome */}
              <div className="flex items-center justify-between px-4 py-3 border-b border-white/5 bg-white/[0.02]">
                <div className="flex gap-2">
                  <div className="size-3 rounded-full bg-[#ff5f56] border border-[#e0443e]" />
                  <div className="size-3 rounded-full bg-[#ffbd2e] border border-[#dea123]" />
                  <div className="size-3 rounded-full bg-[#27c93f] border border-[#1aab29]" />
                </div>
                <div className="flex-1 text-center flex items-center justify-center gap-2">
                  <Lock className="size-3 text-muted-foreground" />
                  <span className="text-xs font-medium text-muted-foreground">omni-ai.com/workspace</span>
                </div>
                <div className="flex gap-2 opacity-0">
                  <div className="size-3" /><div className="size-3" /><div className="size-3" />
                </div>
              </div>

              {/* Application Content */}
              <div className="flex h-[400px]">
                {/* Sidebar mock */}
                <div className="w-64 border-r border-white/5 p-4 hidden md:block bg-black/20">
                  <div className="text-xs font-semibold text-muted-foreground mb-4 px-2 uppercase tracking-wider">Sessions</div>
                  <div className="space-y-1">
                    <div className="px-2 py-1.5 rounded-md bg-white/5 text-sm text-foreground flex items-center gap-2">
                      <Terminal className="size-3.5 text-primary" />
                      Quantum Sim
                    </div>
                    <div className="px-2 py-1.5 rounded-md text-sm text-muted-foreground flex items-center gap-2">
                      <FileText className="size-3.5" />
                      Q3 Report Analysis
                    </div>
                  </div>
                </div>

                {/* Chat mock */}
                <div className="flex-1 p-6 flex flex-col gap-6 overflow-hidden">
                  <div className="flex gap-4">
                    <div className="size-8 rounded-full bg-secondary flex items-center justify-center border border-white/10 shrink-0 shadow-sm">
                      <span className="text-xs font-medium text-muted-foreground">U</span>
                    </div>
                    <div className="flex-1 pt-1">
                      <p className="text-sm font-medium text-foreground">Write a Python simulation of a single qubit applying a Hadamard gate.</p>
                    </div>
                  </div>

                  <div className="flex gap-4">
                    <div className="size-8 rounded-full bg-primary/20 flex items-center justify-center border border-primary/30 shrink-0 shadow-[0_0_10px_rgba(var(--primary),0.2)]">
                      <Sparkles className="size-4 text-primary" />
                    </div>
                    <div className="flex-1 pt-1 space-y-4">
                      <p className="text-sm text-muted-foreground leading-relaxed">I&apos;ll create a simulation of a qubit and apply a Hadamard gate using numpy. The Hadamard gate creates an equal superposition state.</p>
                      <div className="bg-[#050505] rounded-xl p-4 border border-white/5 shadow-inner font-mono text-xs text-muted-foreground overflow-hidden">
                        <div className="flex items-center justify-between mb-3 border-b border-white/5 pb-2">
                          <span className="text-[10px] uppercase tracking-wider text-muted-foreground font-semibold">python</span>
                        </div>
                        <code className="text-[#c678dd]">import</code> <code>numpy </code><code className="text-[#c678dd]">as</code> <code>np</code><br/><br/>
                        <code className="text-[#c678dd]">class</code> <code className="text-[#e5c07b]">Qubit</code><code>:</code><br/>
                        <code>    </code><code className="text-[#c678dd]">def</code> <code className="text-[#61afef]">__init__</code><code>(self):</code><br/>
                        <code>        </code><span className="text-[#5c6370]"># Initialize to |0⟩ state</span><br/>
                        <code>        self.state = np.array([</code><code className="text-[#d19a66]">1</code><code>, </code><code className="text-[#d19a66]">0</code><code>], dtype=np.complex128)</code><br/><br/>
                        <code>    </code><code className="text-[#c678dd]">def</code> <code className="text-[#61afef]">apply_hadamard</code><code>(self):</code><br/>
                        <code>        H = (</code><code className="text-[#d19a66]">1</code><code>/np.sqrt(</code><code className="text-[#d19a66]">2</code><code>)) * np.array([[</code><code className="text-[#d19a66]">1</code><code>, </code><code className="text-[#d19a66]">1</code><code>], [</code><code className="text-[#d19a66]">1</code><code>, </code><code className="text-[#d19a66]">-1</code><code>]])</code><br/>
                        <code>        self.state = np.dot(H, self.state)</code>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="py-32 relative z-10 border-t border-white/5 bg-[#0a0a0c]/50 backdrop-blur-3xl">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div 
            className="text-center mb-20"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, margin: "-100px" }}
            transition={{ duration: 0.8, ease: premiumEasing }}
          >
            <Badge variant="outline" className="mb-6 border-white/10 text-muted-foreground">Capabilities</Badge>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-balance">
              Everything you need to build with AI
            </h2>
            <p className="mt-6 text-lg text-muted-foreground max-w-2xl mx-auto">
              A complete toolkit for AI-powered development, research, and productivity, designed for uncompromising performance.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: Brain,
                title: "Multi-Model Mastery",
                description: "Seamlessly switch between GPT-4, Claude 3.5, and Gemini within the same thread. Leverage the right intelligence for every task."
              },
              {
                icon: FileText,
                title: "Document Intelligence",
                description: "Upload massive PDFs, codebases, and data sets. Get instant, context-aware analysis with accurate citations."
              },
              {
                icon: Code2,
                title: "Developer Grade Coding",
                description: "Write, debug, and refactor code with syntax-aware models. Built-in terminal simulation and execution environment."
              },
              {
                icon: Layers,
                title: "Advanced RAG Pipeline",
                description: "Build custom knowledge bases in seconds. Connect your enterprise documentation for hyper-relevant responses."
              },
              {
                icon: Globe,
                title: "Real-Time Web Search",
                description: "Ground responses with live web data. Bypass knowledge cutoffs with intelligent, transparent source tracing."
              },
              {
                icon: Lock,
                title: "Enterprise Security",
                description: "SOC 2 Type II compliant. Zero data retention policies available. End-to-end encryption for your sensitive IP."
              }
            ].map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: "-50px" }}
                transition={{ duration: 0.7, ease: premiumEasing, delay: index * 0.1 }}
              >
                <Card className="h-full bg-[#0d0d10] border-white/5 hover:border-primary/30 transition-all duration-300 group hover:shadow-[0_0_30px_rgba(var(--primary),0.1)] overflow-hidden relative">
                  <div className="absolute inset-0 bg-gradient-to-br from-primary/5 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
                  <CardHeader>
                    <div className="size-12 rounded-xl bg-[#151518] border border-white/5 flex items-center justify-center mb-4 group-hover:scale-110 group-hover:bg-primary/10 transition-all duration-300 group-hover:border-primary/20">
                      <feature.icon className="size-5 text-muted-foreground group-hover:text-primary transition-colors" />
                    </div>
                    <CardTitle className="text-xl tracking-tight">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="text-muted-foreground text-sm leading-relaxed">
                      {feature.description}
                    </CardDescription>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Stats Section */}
      <section className="py-24 border-y border-white/5 bg-black/20 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {[
              { value: "500K+", label: "Active Developers" },
              { value: "20M+", label: "Queries Processed" },
              { value: "99.99%", label: "Uptime SLA" },
              { value: "<200ms", label: "Average Latency" }
            ].map((stat, index) => (
              <motion.div
                key={stat.label}
                className="text-center"
                initial={{ opacity: 0, scale: 0.95, y: 10 }}
                whileInView={{ opacity: 1, scale: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, ease: premiumEasing, delay: index * 0.1 }}
              >
                <div className="text-4xl sm:text-5xl font-bold text-foreground tracking-tighter mb-2">{stat.value}</div>
                <div className="text-sm font-medium text-muted-foreground uppercase tracking-widest">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-32 relative z-10">
        <div className="absolute top-0 inset-x-0 h-px bg-gradient-to-r from-transparent via-white/10 to-transparent" />
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div 
            className="text-center mb-20"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, ease: premiumEasing }}
          >
            <Badge variant="outline" className="mb-6 border-white/10 text-muted-foreground">Pricing</Badge>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-balance">
              Simple, transparent pricing
            </h2>
            <p className="mt-6 text-lg text-muted-foreground">
              Start building for free. Scale to production seamlessly.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {[
              {
                name: "Hobby",
                price: "$0",
                description: "Perfect for exploring the platform",
                features: ["100 messages/month", "GPT-3.5 & Haiku", "Basic context window", "Community support"],
                cta: "Get Started Free",
                popular: false
              },
              {
                name: "Pro",
                price: "$20",
                description: "For professionals and serious developers",
                features: ["Unlimited messages", "GPT-4, Opus, & Gemini Pro", "Massive context limits", "Priority support", "API access"],
                cta: "Start Pro Trial",
                popular: true
              },
              {
                name: "Enterprise",
                price: "Custom",
                description: "For scaling teams and organizations",
                features: ["Everything in Pro", "SSO & SAML", "Zero data retention", "Dedicated success manager", "99.99% SLA"],
                cta: "Contact Sales",
                popular: false
              }
            ].map((plan, index) => (
              <motion.div
                key={plan.name}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.7, ease: premiumEasing, delay: index * 0.1 }}
                className="flex"
              >
                <Card className={`w-full flex flex-col relative bg-[#0d0d10] ${plan.popular ? 'border-primary/50 shadow-[0_0_40px_rgba(var(--primary),0.15)] ring-1 ring-primary/20' : 'border-white/5'}`}>
                  {plan.popular && (
                    <div className="absolute -top-3 inset-x-0 flex justify-center">
                      <Badge className="bg-primary text-primary-foreground font-semibold px-3 py-0.5 shadow-lg">Most Popular</Badge>
                    </div>
                  )}
                  <CardHeader className="text-center pb-6 pt-8">
                    <CardTitle className="text-xl tracking-tight mb-2">{plan.name}</CardTitle>
                    <div className="mb-4">
                      <span className="text-5xl font-bold tracking-tighter">{plan.price}</span>
                      {plan.price !== "Custom" && <span className="text-muted-foreground font-medium">/mo</span>}
                    </div>
                    <CardDescription className="text-sm">{plan.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="flex flex-col flex-1 space-y-6">
                    <ul className="space-y-4 flex-1">
                      {plan.features.map((feature) => (
                        <li key={feature} className="flex items-start gap-3 text-sm font-medium text-foreground/80">
                          <Check className="size-4 text-primary shrink-0 mt-0.5" />
                          <span>{feature}</span>
                        </li>
                      ))}
                    </ul>
                    <Button 
                      className={`w-full h-11 font-semibold ${plan.popular ? 'glow-primary' : 'bg-white/5 hover:bg-white/10 border border-white/10 text-foreground'}`}
                      variant={plan.popular ? "default" : "secondary"}
                      asChild
                    >
                      <Link href="/register">{plan.cta}</Link>
                    </Button>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Testimonials */}
      <section id="testimonials" className="py-32 bg-[#050505] border-y border-white/5 relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div 
            className="text-center mb-20"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, ease: premiumEasing }}
          >
            <Badge variant="outline" className="mb-6 border-white/10 text-muted-foreground">Wall of Love</Badge>
            <h2 className="text-3xl sm:text-4xl lg:text-5xl font-bold tracking-tight text-balance">
              Trusted by the best
            </h2>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                quote: "Omni AI has fundamentally shifted how our engineering team operates. The seamless model switching is unparalleled.",
                author: "Sarah Chen",
                role: "Staff Engineer, Linear"
              },
              {
                quote: "The RAG pipeline is shockingly fast and accurate. It ingested our entire internal documentation in minutes.",
                author: "Marcus Johnson",
                role: "VP Engineering, Vercel"
              },
              {
                quote: "It feels like a true operating system for AI, not just another chat wrapper. The UI polish is incredible.",
                author: "Emily Park",
                role: "Product Design, Stripe"
              }
            ].map((testimonial, index) => (
              <motion.div
                key={testimonial.author}
                initial={{ opacity: 0, y: 30 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.7, ease: premiumEasing, delay: index * 0.1 }}
              >
                <Card className="h-full bg-[#0a0a0c] border-white/5 hover:border-white/10 transition-colors">
                  <CardContent className="pt-8 flex flex-col justify-between h-full gap-6">
                    <div>
                      <div className="flex gap-1 mb-6">
                        {[...Array(5)].map((_, i) => (
                          <Star key={i} className="size-4 fill-primary text-primary" />
                        ))}
                      </div>
                      <p className="text-foreground/90 text-sm leading-relaxed font-medium">&quot;{testimonial.quote}&quot;</p>
                    </div>
                    <div>
                      <div className="font-semibold text-sm">{testimonial.author}</div>
                      <div className="text-xs text-muted-foreground">{testimonial.role}</div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-32 relative z-10 overflow-hidden">
        <div className="absolute inset-0 bg-primary/5" />
        <div className="absolute left-1/2 bottom-0 -translate-x-1/2 translate-y-1/2 w-[600px] h-[300px] bg-primary/20 rounded-full blur-[100px] opacity-50" />
        
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-20">
          <motion.div
            initial={{ opacity: 0, y: 30 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.8, ease: premiumEasing }}
          >
            <h2 className="text-4xl sm:text-5xl font-bold tracking-tight text-balance mb-6">
              Ready to elevate your workflow?
            </h2>
            <p className="text-xl text-muted-foreground font-medium mb-10 max-w-2xl mx-auto">
              Join elite developers and teams building the future with Omni AI.
            </p>
            <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button size="lg" className="glow-primary font-semibold h-12 px-8 text-primary-foreground w-full sm:w-auto" asChild>
                <Link href="/register">
                  Deploy Intelligence
                  <ArrowRight className="ml-2 size-4" />
                </Link>
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-12 bg-[#050505] relative z-10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div className="flex items-center gap-2">
              <div className="size-6 rounded bg-primary/20 flex items-center justify-center border border-primary/30">
                <Sparkles className="size-3 text-primary" />
              </div>
              <span className="text-base font-semibold tracking-tight">Omni AI</span>
            </div>
            <div className="flex flex-wrap justify-center items-center gap-6 text-sm font-medium text-muted-foreground">
              <Link href="#features" className="hover:text-foreground transition-colors">Features</Link>
              <Link href="#pricing" className="hover:text-foreground transition-colors">Pricing</Link>
              <Link href="/chat" className="hover:text-foreground transition-colors">Demo</Link>
              <Link href="/privacy" className="hover:text-foreground transition-colors">Security</Link>
              <Link href="/terms" className="hover:text-foreground transition-colors">Terms</Link>
            </div>
            <div className="text-sm font-medium text-muted-foreground">
              © {new Date().getFullYear()} Omni AI. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
