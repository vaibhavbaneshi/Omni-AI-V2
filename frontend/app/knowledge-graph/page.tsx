"use client";

import Link from "next/link";
import { Network } from "lucide-react";
import { useRequireAuth } from "@/lib/auth";
import { KnowledgeGraphPanel } from "@/components/chat/knowledge-graph-panel";
import { Button } from "@/components/ui/button";

export default function KnowledgeGraphPage() {
  const { ready, authenticated } = useRequireAuth();

  if (!ready || !authenticated) return <div className="min-h-screen bg-background" />;

  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <div className="mx-auto max-w-5xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold flex items-center gap-2">
              <Network className="size-6 text-primary" />
              Knowledge Graph
            </h1>
            <p className="text-sm text-muted-foreground mt-1">Explore entities and relationships across your workspace</p>
          </div>
          <Link href="/dashboard"><Button variant="outline" size="sm">Dashboard</Button></Link>
        </div>
        <KnowledgeGraphPanel embedded workspaceId="default" />
      </div>
    </div>
  );
}
