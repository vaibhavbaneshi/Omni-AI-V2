"use client";

import { useCallback, useEffect, useState, type PointerEvent as ReactPointerEvent } from "react";

import { useMediaQuery } from "@/hooks/useMediaQuery";

export const SIDEBAR_WIDTH_KEY = "omni-ai-sidebar-width";
export const SIDEBAR_MIN_WIDTH = 220;
export const SIDEBAR_MAX_WIDTH = 520;
export const SIDEBAR_DEFAULT_WIDTH = 280;
export const SIDEBAR_DESKTOP_QUERY = "(min-width: 768px)";

function readSidebarWidth() {
  if (typeof window === "undefined") return SIDEBAR_DEFAULT_WIDTH;
  const stored = Number(window.localStorage.getItem(SIDEBAR_WIDTH_KEY));
  if (!Number.isFinite(stored)) return SIDEBAR_DEFAULT_WIDTH;
  return Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, stored));
}

function clampWidth(value: number) {
  return Math.min(SIDEBAR_MAX_WIDTH, Math.max(SIDEBAR_MIN_WIDTH, value));
}

export function useResizableSidebar() {
  const isDesktop = useMediaQuery(SIDEBAR_DESKTOP_QUERY);
  const [open, setOpen] = useState(false);
  const [width, setWidth] = useState(SIDEBAR_DEFAULT_WIDTH);
  const [isResizing, setIsResizing] = useState(false);

  useEffect(() => {
    setWidth(readSidebarWidth());
  }, []);

  useEffect(() => {
    setOpen(isDesktop);
  }, [isDesktop]);

  const onResizeStart = useCallback((event: ReactPointerEvent<HTMLElement>) => {
    if (!isDesktop) return;
    event.preventDefault();
    event.currentTarget.setPointerCapture(event.pointerId);
    setIsResizing(true);
  }, [isDesktop]);

  useEffect(() => {
    if (!isResizing) return;

    const handlePointerMove = (event: PointerEvent) => {
      const nextWidth = clampWidth(event.clientX);
      setWidth(nextWidth);
      window.localStorage.setItem(SIDEBAR_WIDTH_KEY, String(nextWidth));
    };

    const handlePointerUp = () => setIsResizing(false);

    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);

    return () => {
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("pointermove", handlePointerMove);
      window.removeEventListener("pointerup", handlePointerUp);
      window.removeEventListener("pointercancel", handlePointerUp);
    };
  }, [isResizing]);

  const closeSidebar = useCallback(() => setOpen(false), []);
  const openSidebar = useCallback(() => setOpen(true), []);

  return {
    width,
    isResizing,
    open,
    setOpen,
    isDesktop,
    onResizeStart,
    closeSidebar,
    openSidebar,
  };
}
