"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Bell, Loader2 } from "lucide-react";
import { useNotifications } from "@/hooks/useNotifications";
import { formatRelativeTime } from "@/lib/format-relative-time";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

type NotificationsBellProps = {
  enabled?: boolean;
};

function isInternalLink(link?: string | null): link is string {
  return Boolean(link && link.startsWith("/") && !link.startsWith("//"));
}

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
        <Button type="button" variant="ghost" size="icon" className="relative" aria-label="Notifications">
          <Bell className="size-4" />
          {unreadCount > 0 && (
            <span className="absolute -right-0.5 -top-0.5 flex size-4 items-center justify-center rounded-full bg-destructive text-[10px] font-medium text-destructive-foreground">
              {unreadCount > 9 ? "9+" : unreadCount}
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuGroup>
          <DropdownMenuLabel>Notifications</DropdownMenuLabel>
          {loading ? (
            <DropdownMenuItem disabled className="justify-center py-4">
              <Loader2 className="size-4 animate-spin text-muted-foreground" />
            </DropdownMenuItem>
          ) : error ? (
            <DropdownMenuItem disabled className="whitespace-normal text-xs text-destructive">
              {error}
            </DropdownMenuItem>
          ) : notifications.length === 0 ? (
            <DropdownMenuItem disabled className="text-xs text-muted-foreground">
              No notifications yet.
            </DropdownMenuItem>
          ) : (
            notifications.map((item) => {
              const label = item.body || item.title;
              const content = (
                <>
                  <span className={cn("text-sm", !item.read ? "font-medium" : "text-muted-foreground")}>
                    {label}
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    {formatRelativeTime(item.created_at)}
                    {!item.read ? " · unread" : " · read"}
                  </span>
                </>
              );

              if (isInternalLink(item.link)) {
                return (
                  <DropdownMenuItem
                    key={item.id}
                    asChild
                    className={cn("flex flex-col items-start gap-1 py-2", !item.read && "bg-primary/5")}
                  >
                    <Link
                      href={item.link}
                      onClick={() => {
                        setOpen(false);
                        void markRead(item.id);
                      }}
                    >
                      {content}
                    </Link>
                  </DropdownMenuItem>
                );
              }

              return (
                <DropdownMenuItem
                  key={item.id}
                  className={cn("flex flex-col items-start gap-1 py-2", !item.read && "bg-primary/5")}
                  onClick={() => void markRead(item.id)}
                >
                  {content}
                </DropdownMenuItem>
              );
            })
          )}
        </DropdownMenuGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
