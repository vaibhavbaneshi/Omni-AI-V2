"use client";

import { Network } from "lucide-react";
import { BackButton } from "@/components/navigation/back-button";
import { useRequireAuth } from "@/lib/auth";
import { KnowledgeGraphPanel } from "@/components/chat/knowledge-graph-panel";

export default function KnowledgeGraphPage() {
  const { session, ready, authenticated } = useRequireAuth();

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
          <BackButton variant="outline" />
        </div>
        <KnowledgeGraphPanel embedded workspaceId="default" token={session?.token} />
      </div>
    </div>
  );
}
