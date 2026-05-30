import { useEffect, useState } from "react";
import { fetchModels, type ModelDefinition } from "@/lib/api";

const FALLBACK_MODELS: ModelDefinition[] = [
  {
    id: "auto",
    name: "Auto Route",
    provider: "router",
    model_name: "auto",
    description: "Automatically pick the best model for your task.",
    roles: ["auto"],
    badge: "Smart",
    available: true,
  },
  {
    id: "llama-70b",
    name: "Llama 3.3 70B",
    provider: "groq",
    model_name: "llama-3.3-70b-versatile",
    description: "Best for reasoning, research, and general chat.",
    roles: ["general", "reasoning"],
    badge: "Default",
    available: true,
  },
];

export function useModels() {
  const [models, setModels] = useState<ModelDefinition[]>(FALLBACK_MODELS);
  const [routingEnabled, setRoutingEnabled] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    fetchModels()
      .then((payload) => {
        if (cancelled) return;
        if (payload.models.length > 0) {
          setModels(payload.models.filter((model) => model.id === "auto" || model.available));
        }
        setRoutingEnabled(payload.routing_enabled);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : "Failed to load models");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  return { models, routingEnabled, loading, error };
}
