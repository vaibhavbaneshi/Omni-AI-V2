import { useEffect, useState } from "react";

/** Local-time greeting (uses the browser timezone). */
export function getTimeOfDayGreeting(date = new Date()): string {
  const hour = date.getHours();
  if (hour >= 5 && hour < 12) return "Good morning";
  if (hour >= 12 && hour < 17) return "Good afternoon";
  return "Good evening";
}

export function useTimeOfDayGreeting(): string {
  const [greeting, setGreeting] = useState("Hello");

  useEffect(() => {
    setGreeting(getTimeOfDayGreeting());
  }, []);

  return greeting;
}
