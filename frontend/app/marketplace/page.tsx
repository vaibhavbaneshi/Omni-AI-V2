"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, Store } from "lucide-react";
import { useRequireAuth } from "@/lib/auth";
import { installMarketplaceTemplate, listMarketplaceTemplates } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function MarketplacePage() {
  const { ready, authenticated } = useRequireAuth();
  const [templates, setTemplates] = useState<Array<Record<string, unknown>>>([]);
  const [loading, setLoading] = useState(true);
  const [installing, setInstalling] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listMarketplaceTemplates();
      setTemplates(data.templates);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load marketplace.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (ready && authenticated) void load();
  }, [ready, authenticated, load]);

  const handleInstall = async (slug: string) => {
    setInstalling(slug);
    setError(null);
    try {
      await installMarketplaceTemplate(slug);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Install failed.");
    } finally {
      setInstalling(null);
    }
  };

  if (!ready || !authenticated) return <div className="min-h-screen bg-background" />;

  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold flex items-center gap-2">
              <Store className="size-6 text-primary" />
              Agent Marketplace
            </h1>
            <p className="text-sm text-muted-foreground mt-1">Browse and install reusable agent templates</p>
          </div>
          <Link href="/agents"><Button variant="outline" size="sm">My Agents</Button></Link>
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        {loading ? (
          <Loader2 className="size-6 animate-spin mx-auto text-muted-foreground" />
        ) : (
          <div className="grid gap-3 sm:grid-cols-2">
            {templates.map((template) => {
              const slug = String(template.slug ?? "");
              return (
                <Card key={slug} className="border-white/10 bg-card/65">
                  <CardHeader>
                    <CardTitle className="text-base">{String(template.name ?? slug)}</CardTitle>
                    <p className="text-xs text-muted-foreground">{String(template.category ?? "")}</p>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <p className="text-sm text-muted-foreground">{String(template.description ?? "")}</p>
                    <Button size="sm" disabled={installing === slug} onClick={() => void handleInstall(slug)}>
                      {installing === slug ? <Loader2 className="size-4 animate-spin mr-1" /> : null}
                      Install
                    </Button>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
