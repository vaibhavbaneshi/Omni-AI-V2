"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Shield, Loader2 } from "lucide-react";
import { useRequireAuth } from "@/lib/auth";
import { assignUserRole, getAuditUsers } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

const ROLES = ["admin", "manager", "editor", "viewer"] as const;

export default function RbacAdminPage() {
  const { session, ready, authenticated } = useRequireAuth();
  const [users, setUsers] = useState<Array<{ id: number; email: string; username: string; role: string }>>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [savingId, setSavingId] = useState<number | null>(null);

  useEffect(() => {
    if (!authenticated) return;
    getAuditUsers(200, 0)
      .then((data) => setUsers(data.users))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load users."))
      .finally(() => setLoading(false));
  }, [authenticated]);

  const handleRoleChange = async (userId: number, role: string) => {
    setSavingId(userId);
    setError(null);
    try {
      await assignUserRole(userId, role);
      setUsers((prev) => prev.map((user) => (user.id === userId ? { ...user, role } : user)));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Role update failed.");
    } finally {
      setSavingId(null);
    }
  };

  if (!ready || !authenticated) return <div className="min-h-screen bg-background" />;

  return (
    <div className="min-h-screen bg-background px-4 py-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold flex items-center gap-2">
              <Shield className="size-6 text-primary" />
              RBAC Admin
            </h1>
            <p className="text-sm text-muted-foreground mt-1">Assign roles — admin only</p>
          </div>
          <Link href="/dashboard"><Button variant="outline" size="sm">Back</Button></Link>
        </div>
        {error && <p className="text-sm text-destructive">{error}</p>}
        <Card className="border-white/10 bg-card/65">
          <CardHeader><CardTitle>Users</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            {loading && <div className="flex gap-2 text-sm text-muted-foreground"><Loader2 className="size-4 animate-spin" />Loading…</div>}
            {users.map((user) => (
              <div key={user.id} className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/5 px-3 py-2">
                <div>
                  <p className="font-medium text-sm">{user.email}</p>
                  <p className="text-xs text-muted-foreground">@{user.username}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant="outline">{user.role}</Badge>
                  <select
                    className="h-8 rounded-md border border-white/10 bg-background px-2 text-xs"
                    value={user.role}
                    disabled={savingId === user.id}
                    onChange={(e) => void handleRoleChange(user.id, e.target.value)}
                  >
                    {ROLES.map((role) => (
                      <option key={role} value={role}>{role}</option>
                    ))}
                  </select>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
