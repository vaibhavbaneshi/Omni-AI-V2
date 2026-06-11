"use client";

import { useEffect, useState } from "react";
import { Bell, Loader2 } from "lucide-react";
import { useNotifications } from "@/hooks/useNotifications";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

type NotificationsBellProps = {
  enabled?: boolean;
};

export function NotificationsBell({ enabled = true }: NotificationsBellProps) {
  const { notifications, unreadCount, loading, error, loadNotifications, markRead } = useNotifications(enabled);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    if (open && enabled) {
      void loadNotifications();
    }
  }, [open, enabled, loadNotifications]);

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
          <Bell className="size-4" />
          {unreadCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex size-4 items-center justify-center rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel>Notifications</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {loading ? (
          <div className="flex justify-center py-6">
            <Loader2 className="size-4 animate-spin text-muted-foreground" />
          </div>
        ) : error ? (
          <p className="px-2 py-3 text-xs text-destructive">{error}</p>
        ) : notifications.length === 0 ? (
          <p className="px-2 py-3 text-xs text-muted-foreground">No notifications yet.</p>
        ) : (
          notifications.map((item) => (
            <DropdownMenuItem
              key={item.id}
              className={cn("flex flex-col items-start gap-1 py-2", !item.read && "bg-primary/5")}
              onClick={() => void markRead(item.id)}
            >
              <span className={cn("text-sm", !item.read ? "font-medium" : "text-muted-foreground")}>
                {item.body || item.title}
              </span>
              <span className="text-[11px] text-muted-foreground">
                {formatRelativeTime(item.created_at)}
                {!item.read ? " · unread" : " · read"}
              </span>
            </DropdownMenuItem>
          ))
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
