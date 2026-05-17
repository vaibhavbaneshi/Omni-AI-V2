"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import { 
  Sparkles, 
  Brain, 
  FileText, 
  Code2, 
  MessageSquare,
  ArrowRight,
  Check,
  Star,
  ChevronRight,
  Globe,
  Layers,
  Lock
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

const fadeInUp = {
  initial: { opacity: 0, y: 20 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.5 }
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
    <div className="min-h-screen bg-background">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 glass">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-2">
              <div className="size-8 rounded-lg bg-primary/20 flex items-center justify-center">
                <Sparkles className="size-5 text-primary" />
              </div>
              <span className="text-xl font-semibold text-foreground">Omni AI</span>
            </div>
            
            <div className="hidden md:flex items-center gap-8">
              <Link href="#features" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Features
              </Link>
              <Link href="#pricing" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Pricing
              </Link>
              <Link href="#testimonials" className="text-sm text-muted-foreground hover:text-foreground transition-colors">
                Testimonials
              </Link>
            </div>

            <div className="flex items-center gap-3">
              <Button variant="ghost" size="sm" asChild>
                <Link href="/login">Sign In</Link>
              </Button>
              <Button size="sm" asChild>
                <Link href="/register">
                  Get Started
                  <ArrowRight data-icon="inline-end" />
                </Link>
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative pt-32 pb-20 overflow-hidden">
        {/* Background gradient */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,oklch(0.25_0.08_280),transparent_60%)]" />
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div 
            className="text-center max-w-4xl mx-auto"
            initial="initial"
            animate="animate"
            variants={staggerContainer}
          >
            <motion.div variants={fadeInUp}>
              <Badge variant="secondary" className="mb-6">
                <Star className="size-3 mr-1" />
                Trusted by 50,000+ developers
              </Badge>
            </motion.div>
            
            <motion.h1 
              variants={fadeInUp}
              className="text-4xl sm:text-5xl lg:text-7xl font-bold tracking-tight text-balance"
            >
              Your Intelligent
              <span className="text-gradient block mt-2">AI Operating System</span>
            </motion.h1>
            
            <motion.p 
              variants={fadeInUp}
              className="mt-6 text-lg sm:text-xl text-muted-foreground max-w-2xl mx-auto text-pretty"
            >
              The most powerful AI workspace for developers and power users. 
              Chat with any model, analyze documents, generate code, and build faster than ever.
            </motion.p>
            
            <motion.div 
              variants={fadeInUp}
              className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4"
            >
              <Button size="lg" className="w-full sm:w-auto glow-primary" asChild>
                <Link href="/register">
                  Start Building Free
                  <ArrowRight data-icon="inline-end" />
                </Link>
              </Button>
              <Button variant="outline" size="lg" className="w-full sm:w-auto" asChild>
                <Link href="/chat">
                  Try Demo
                  <ChevronRight data-icon="inline-end" />
                </Link>
              </Button>
            </motion.div>

            <motion.div 
              variants={fadeInUp}
              className="mt-8 flex items-center justify-center gap-6 text-sm text-muted-foreground"
            >
              <div className="flex items-center gap-2">
                <Check className="size-4 text-success" />
                <span>No credit card required</span>
              </div>
              <div className="flex items-center gap-2">
                <Check className="size-4 text-success" />
                <span>Free tier forever</span>
              </div>
            </motion.div>
          </motion.div>

          {/* Hero Image/Preview */}
          <motion.div 
            className="mt-20 relative"
            initial={{ opacity: 0, y: 40 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.4 }}
          >
            <div className="relative rounded-xl border border-border/50 bg-card/50 backdrop-blur-sm overflow-hidden shadow-2xl">
              <div className="absolute inset-0 bg-gradient-to-b from-primary/5 to-transparent" />
              <div className="p-2">
                {/* Window chrome */}
                <div className="flex items-center gap-2 px-3 py-2 border-b border-border/50">
                  <div className="flex gap-1.5">
                    <div className="size-3 rounded-full bg-destructive/60" />
                    <div className="size-3 rounded-full bg-warning/60" />
                    <div className="size-3 rounded-full bg-success/60" />
                  </div>
                  <div className="flex-1 text-center">
                    <span className="text-xs text-muted-foreground">Omni AI Chat</span>
                  </div>
                </div>
                {/* Chat preview */}
                <div className="p-6 space-y-4">
                  <div className="flex gap-3">
                    <div className="size-8 rounded-full bg-primary/20 flex items-center justify-center shrink-0">
                      <MessageSquare className="size-4 text-primary" />
                    </div>
                    <div className="flex-1 bg-secondary/50 rounded-lg p-4">
                      <p className="text-sm text-foreground">Explain quantum computing in simple terms and write a Python simulation of a qubit.</p>
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <div className="size-8 rounded-full bg-gradient-to-br from-primary to-chart-2 flex items-center justify-center shrink-0">
                      <Sparkles className="size-4 text-primary-foreground" />
                    </div>
                    <div className="flex-1 bg-accent/30 rounded-lg p-4 border border-border/30">
                      <p className="text-sm text-foreground mb-3">Quantum computing uses quantum bits or qubits that can exist in multiple states simultaneously...</p>
                      <div className="bg-background/50 rounded-md p-3 font-mono text-xs text-muted-foreground">
                        <code>import numpy as np</code><br/>
                        <code className="text-primary">class</code> <code className="text-chart-2">Qubit</code><code>:</code><br/>
                        <code>    </code><code className="text-primary">def</code> <code>__init__(self):</code>
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
      <section id="features" className="py-24 relative">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div 
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <Badge variant="outline" className="mb-4">Features</Badge>
            <h2 className="text-3xl sm:text-4xl font-bold text-balance">
              Everything you need to build with AI
            </h2>
            <p className="mt-4 text-lg text-muted-foreground max-w-2xl mx-auto">
              A complete toolkit for AI-powered development, research, and productivity.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                icon: Brain,
                title: "Multi-Model Support",
                description: "Access GPT-4, Claude, Gemini, and more from a single interface. Switch models mid-conversation."
              },
              {
                icon: FileText,
                title: "Document Intelligence",
                description: "Upload PDFs, code files, and data. Get instant analysis, summaries, and insights."
              },
              {
                icon: Code2,
                title: "Code Generation",
                description: "Generate, debug, and refactor code in any language. Built-in syntax highlighting and execution."
              },
              {
                icon: Layers,
                title: "RAG Pipeline",
                description: "Build custom knowledge bases. Connect your docs for context-aware AI responses."
              },
              {
                icon: Globe,
                title: "Web Search",
                description: "Ground responses with real-time web data. Citations and source verification included."
              },
              {
                icon: Lock,
                title: "Enterprise Security",
                description: "SOC 2 compliant. Data encryption, SSO, and audit logs for enterprise teams."
              }
            ].map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card className="h-full bg-card/50 border-border/50 hover:border-primary/30 transition-colors group">
                  <CardHeader>
                    <div className="size-12 rounded-lg bg-primary/10 flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                      <feature.icon className="size-6 text-primary" />
                    </div>
                    <CardTitle className="text-lg">{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <CardDescription className="text-muted-foreground">
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
      <section className="py-16 border-y border-border/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-8">
            {[
              { value: "50K+", label: "Active Users" },
              { value: "10M+", label: "Messages Sent" },
              { value: "99.9%", label: "Uptime" },
              { value: "150+", label: "Countries" }
            ].map((stat, index) => (
              <motion.div
                key={stat.label}
                className="text-center"
                initial={{ opacity: 0, scale: 0.9 }}
                whileInView={{ opacity: 1, scale: 1 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <div className="text-3xl sm:text-4xl font-bold text-gradient">{stat.value}</div>
                <div className="mt-1 text-sm text-muted-foreground">{stat.label}</div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div 
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <Badge variant="outline" className="mb-4">Pricing</Badge>
            <h2 className="text-3xl sm:text-4xl font-bold text-balance">
              Simple, transparent pricing
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Start free, scale as you grow.
            </p>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
            {[
              {
                name: "Free",
                price: "$0",
                description: "Perfect for trying out Omni AI",
                features: ["100 messages/month", "GPT-3.5 access", "Basic file uploads", "Community support"],
                cta: "Get Started",
                popular: false
              },
              {
                name: "Pro",
                price: "$20",
                description: "For professionals and power users",
                features: ["Unlimited messages", "All models (GPT-4, Claude, etc.)", "Advanced RAG features", "Priority support", "API access"],
                cta: "Start Pro Trial",
                popular: true
              },
              {
                name: "Enterprise",
                price: "Custom",
                description: "For teams and organizations",
                features: ["Everything in Pro", "SSO & SAML", "Custom integrations", "Dedicated support", "SLA guarantee"],
                cta: "Contact Sales",
                popular: false
              }
            ].map((plan, index) => (
              <motion.div
                key={plan.name}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card className={`h-full relative ${plan.popular ? 'border-primary glow-primary' : 'border-border/50'}`}>
                  {plan.popular && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                      <Badge className="bg-primary text-primary-foreground">Most Popular</Badge>
                    </div>
                  )}
                  <CardHeader className="text-center pb-2">
                    <CardTitle className="text-lg">{plan.name}</CardTitle>
                    <div className="mt-4">
                      <span className="text-4xl font-bold">{plan.price}</span>
                      {plan.price !== "Custom" && <span className="text-muted-foreground">/month</span>}
                    </div>
                    <CardDescription>{plan.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <ul className="space-y-3">
                      {plan.features.map((feature) => (
                        <li key={feature} className="flex items-center gap-2 text-sm">
                          <Check className="size-4 text-success shrink-0" />
                          <span>{feature}</span>
                        </li>
                      ))}
                    </ul>
                    <Button 
                      className="w-full mt-6" 
                      variant={plan.popular ? "default" : "outline"}
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
      <section id="testimonials" className="py-24 bg-secondary/30">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div 
            className="text-center mb-16"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <Badge variant="outline" className="mb-4">Testimonials</Badge>
            <h2 className="text-3xl sm:text-4xl font-bold text-balance">
              Loved by developers worldwide
            </h2>
          </motion.div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                quote: "Omni AI has completely transformed how I write code. The multi-model support is a game changer.",
                author: "Sarah Chen",
                role: "Senior Engineer at Stripe"
              },
              {
                quote: "Finally, an AI tool that understands context. The RAG features are incredibly powerful.",
                author: "Marcus Johnson",
                role: "CTO at TechStart"
              },
              {
                quote: "The best AI workspace I've used. Clean interface, fast responses, and reliable.",
                author: "Emily Park",
                role: "Product Lead at Vercel"
              }
            ].map((testimonial, index) => (
              <motion.div
                key={testimonial.author}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.5, delay: index * 0.1 }}
              >
                <Card className="h-full bg-card/50">
                  <CardContent className="pt-6">
                    <div className="flex gap-1 mb-4">
                      {[...Array(5)].map((_, i) => (
                        <Star key={i} className="size-4 fill-warning text-warning" />
                      ))}
                    </div>
                    <p className="text-foreground mb-4">&quot;{testimonial.quote}&quot;</p>
                    <div>
                      <div className="font-medium">{testimonial.author}</div>
                      <div className="text-sm text-muted-foreground">{testimonial.role}</div>
                    </div>
                  </CardContent>
                </Card>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-24">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.5 }}
          >
            <h2 className="text-3xl sm:text-4xl font-bold text-balance">
              Ready to supercharge your workflow?
            </h2>
            <p className="mt-4 text-lg text-muted-foreground">
              Join thousands of developers building with Omni AI.
            </p>
            <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-4">
              <Button size="lg" className="glow-primary" asChild>
                <Link href="/register">
                  Get Started Free
                  <ArrowRight data-icon="inline-end" />
                </Link>
              </Button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border/50 py-12">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="size-8 rounded-lg bg-primary/20 flex items-center justify-center">
                <Sparkles className="size-5 text-primary" />
              </div>
              <span className="text-lg font-semibold">Omni AI</span>
            </div>
            <div className="flex items-center gap-6 text-sm text-muted-foreground">
              <Link href="#" className="hover:text-foreground transition-colors">Privacy</Link>
              <Link href="#" className="hover:text-foreground transition-colors">Terms</Link>
              <Link href="#" className="hover:text-foreground transition-colors">Docs</Link>
              <Link href="#" className="hover:text-foreground transition-colors">Support</Link>
            </div>
            <div className="text-sm text-muted-foreground">
              © 2026 Omni AI. All rights reserved.
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
