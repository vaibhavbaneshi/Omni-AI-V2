import { useCallback, useEffect, useState } from "react";
import {
  getNotificationUnreadCount,
  listNotifications,
  markNotificationRead,
  type NotificationRecord,
} from "@/lib/api";

const POLL_MS = 60_000;

export function useNotifications(enabled = true) {
  const [notifications, setNotifications] = useState<NotificationRecord[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const refreshUnreadCount = useCallback(async () => {
    if (!enabled) return;
    try {
      const data = await getNotificationUnreadCount();
      setUnreadCount(data.count);
    } catch {
      // Keep last known count on poll failure.
    }
  }, [enabled]);

  const loadNotifications = useCallback(async () => {
    if (!enabled) return;
    setLoading(true);
    setError(null);
    try {
      const data = await listNotifications();
      setNotifications(data.notifications.slice(0, 10));
      await refreshUnreadCount();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load notifications.";
      setError(
        message.includes("500")
          ? "Notifications are unavailable. Ensure the backend migration 20260608_0016 has been applied."
          : message
      );
    } finally {
      setLoading(false);
    }
  }, [enabled, refreshUnreadCount]);

  const markRead = useCallback(async (notificationId: number) => {
    try {
      await markNotificationRead(notificationId);
      setNotifications((prev) =>
        prev.map((item) => (item.id === notificationId ? { ...item, read: true } : item))
      );
      setUnreadCount((prev) => Math.max(0, prev - 1));
    } catch {
      // Keep UI responsive if mark-read fails.
    }
  }, []);

  useEffect(() => {
    if (!enabled) return;
    void refreshUnreadCount();
    const timer = window.setInterval(() => void refreshUnreadCount(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [enabled, refreshUnreadCount]);

  return {
    notifications,
    unreadCount,
    loading,
    error,
    loadNotifications,
    markRead,
    refreshUnreadCount,
  };
}
