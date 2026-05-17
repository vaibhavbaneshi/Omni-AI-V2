"use client";

import { motion } from "framer-motion";
import Link from "next/link";
import {
  Sparkles,
  MessageSquare,
  FileText,
  Zap,
  TrendingUp,
  Clock,
  ArrowRight,
  Settings,
  CreditCard,
  Users,
  BarChart3,
  Calendar,
  ChevronRight,
  Plus,
  Brain,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";

const stats = [
  {
    title: "Total Messages",
    value: "12,847",
    change: "+12%",
    changeType: "positive" as const,
    icon: MessageSquare,
  },
  {
    title: "Documents Analyzed",
    value: "156",
    change: "+8%",
    changeType: "positive" as const,
    icon: FileText,
  },
  {
    title: "API Calls",
    value: "45.2K",
    change: "+24%",
    changeType: "positive" as const,
    icon: Zap,
  },
  {
    title: "Active Sessions",
    value: "3",
    change: "0%",
    changeType: "neutral" as const,
    icon: Users,
  },
];

const recentChats = [
  {
    id: "1",
    title: "React Component Optimization",
    preview: "How do I optimize this component for better performance?",
    model: "GPT-4",
    time: "30 min ago",
  },
  {
    id: "2",
    title: "Python Data Analysis",
    preview: "Can you help with pandas dataframe operations?",
    model: "Claude 3",
    time: "2 hours ago",
  },
  {
    id: "3",
    title: "API Design Best Practices",
    preview: "RESTful vs GraphQL comparison for our new service",
    model: "GPT-4",
    time: "Yesterday",
  },
  {
    id: "4",
    title: "Database Schema Review",
    preview: "Looking for feedback on this PostgreSQL schema",
    model: "GPT-4",
    time: "2 days ago",
  },
];

const usageByModel = [
  { model: "GPT-4", usage: 45, color: "bg-primary" },
  { model: "Claude 3", usage: 30, color: "bg-chart-2" },
  { model: "GPT-3.5", usage: 20, color: "bg-chart-3" },
  { model: "Gemini", usage: 5, color: "bg-chart-4" },
];

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b border-border bg-background/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-4">
              <Link href="/" className="flex items-center gap-2">
                <div className="size-8 rounded-lg bg-primary/20 flex items-center justify-center">
                  <Sparkles className="size-5 text-primary" />
                </div>
                <span className="text-xl font-semibold">Omni AI</span>
              </Link>
              <Separator orientation="vertical" className="h-6" />
              <span className="text-muted-foreground">Dashboard</span>
            </div>

            <div className="flex items-center gap-3">
              <Button variant="outline" size="sm" asChild>
                <Link href="/chat">
                  <Plus data-icon="inline-start" />
                  New Chat
                </Link>
              </Button>
              <Button variant="ghost" size="icon" asChild>
                <Link href="/settings">
                  <Settings className="size-4" />
                </Link>
              </Button>
              <Avatar className="size-8 cursor-pointer">
                <AvatarFallback className="bg-primary/20 text-primary text-sm">
                  JD
                </AvatarFallback>
              </Avatar>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Welcome Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <h1 className="text-3xl font-bold mb-2">Welcome back, John</h1>
          <p className="text-muted-foreground">
            Here&apos;s an overview of your AI workspace activity
          </p>
        </motion.div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
          {stats.map((stat, index) => (
            <motion.div
              key={stat.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <Card className="bg-card/50 border-border/50">
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between mb-4">
                    <div className="size-10 rounded-lg bg-primary/10 flex items-center justify-center">
                      <stat.icon className="size-5 text-primary" />
                    </div>
                    <Badge
                      variant={stat.changeType === "positive" ? "secondary" : "outline"}
                      className={
                        stat.changeType === "positive"
                          ? "text-success bg-success/10"
                          : ""
                      }
                    >
                      <TrendingUp className="size-3 mr-1" />
                      {stat.change}
                    </Badge>
                  </div>
                  <div>
                    <p className="text-2xl font-bold">{stat.value}</p>
                    <p className="text-sm text-muted-foreground">{stat.title}</p>
                  </div>
                </CardContent>
              </Card>
            </motion.div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Recent Chats */}
          <motion.div
            className="lg:col-span-2"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
          >
            <Card className="bg-card/50 border-border/50">
              <CardHeader className="flex flex-row items-center justify-between">
                <div>
                  <CardTitle className="text-lg">Recent Chats</CardTitle>
                  <CardDescription>Your latest conversations</CardDescription>
                </div>
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/chat">
                    View All
                    <ChevronRight data-icon="inline-end" />
                  </Link>
                </Button>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {recentChats.map((chat) => (
                    <Link
                      key={chat.id}
                      href={`/chat?id=${chat.id}`}
                      className="flex items-start gap-4 p-3 rounded-lg hover:bg-accent/50 transition-colors group"
                    >
                      <div className="size-10 rounded-lg bg-secondary flex items-center justify-center shrink-0">
                        <MessageSquare className="size-5 text-muted-foreground" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <p className="font-medium truncate">{chat.title}</p>
                          <Badge variant="outline" className="text-xs shrink-0">
                            {chat.model}
                          </Badge>
                        </div>
                        <p className="text-sm text-muted-foreground truncate">
                          {chat.preview}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground shrink-0">
                        <Clock className="size-3" />
                        {chat.time}
                      </div>
                    </Link>
                  ))}
                </div>
              </CardContent>
            </Card>
          </motion.div>

          {/* Usage by Model */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
          >
            <Card className="bg-card/50 border-border/50 h-full">
              <CardHeader>
                <CardTitle className="text-lg">Usage by Model</CardTitle>
                <CardDescription>This month&apos;s distribution</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {usageByModel.map((item) => (
                    <div key={item.model} className="space-y-2">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">{item.model}</span>
                        <span className="text-muted-foreground">{item.usage}%</span>
                      </div>
                      <div className="h-2 rounded-full bg-secondary overflow-hidden">
                        <motion.div
                          className={`h-full rounded-full ${item.color}`}
                          initial={{ width: 0 }}
                          animate={{ width: `${item.usage}%` }}
                          transition={{ duration: 0.8, delay: 0.6 }}
                        />
                      </div>
                    </div>
                  ))}
                </div>

                <Separator className="my-6" />

                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Current Plan</span>
                    <Badge>Pro</Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Messages Left</span>
                    <span className="font-medium">Unlimited</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-muted-foreground">Renewal Date</span>
                    <span className="text-sm">June 15, 2026</span>
                  </div>
                </div>

                <Button variant="outline" className="w-full mt-4" asChild>
                  <Link href="/settings/billing">
                    <CreditCard data-icon="inline-start" />
                    Manage Billing
                  </Link>
                </Button>
              </CardContent>
            </Card>
          </motion.div>
        </div>

        {/* Quick Actions */}
        <motion.div
          className="mt-8"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.6 }}
        >
          <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              {
                title: "Start New Chat",
                description: "Begin a conversation with AI",
                icon: MessageSquare,
                href: "/chat",
                color: "bg-primary/10 text-primary",
              },
              {
                title: "Upload Document",
                description: "Analyze PDFs and files",
                icon: FileText,
                href: "/chat",
                color: "bg-chart-2/10 text-chart-2",
              },
              {
                title: "View Analytics",
                description: "Track your usage stats",
                icon: BarChart3,
                href: "/settings/usage",
                color: "bg-chart-3/10 text-chart-3",
              },
              {
                title: "Manage Models",
                description: "Configure AI preferences",
                icon: Brain,
                href: "/settings",
                color: "bg-chart-4/10 text-chart-4",
              },
            ].map((action) => (
              <Link key={action.title} href={action.href}>
                <Card className="bg-card/50 border-border/50 hover:border-primary/30 transition-colors h-full cursor-pointer group">
                  <CardContent className="pt-6">
                    <div
                      className={`size-12 rounded-lg ${action.color} flex items-center justify-center mb-4`}
                    >
                      <action.icon className="size-6" />
                    </div>
                    <h3 className="font-medium mb-1 group-hover:text-primary transition-colors">
                      {action.title}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                      {action.description}
                    </p>
                  </CardContent>
                </Card>
              </Link>
            ))}
          </div>
        </motion.div>
      </main>
    </div>
  );
}
