"use client";

import { useRouter } from "next/navigation";
import { ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

type BackButtonProps = {
  fallbackHref?: string;
  className?: string;
  label?: string;
  variant?: "icon" | "outline";
};

export function BackButton({
  fallbackHref = "/dashboard",
  className,
  label = "Back",
  variant = "icon",
}: BackButtonProps) {
  const router = useRouter();

  const handleBack = () => {
    if (typeof window !== "undefined" && window.history.length > 1) {
      router.back();
      return;
    }
    router.push(fallbackHref);
  };

  if (variant === "icon") {
    return (
      <Button
        type="button"
        variant="ghost"
        size="icon"
        aria-label="Go back"
        className={className}
        onClick={handleBack}
      >
        <ChevronLeft className="size-4" />
      </Button>
    );
  }

  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      className={cn(className)}
      onClick={handleBack}
    >
      {label}
    </Button>
  );
}
