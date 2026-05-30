export const MODEL_PREFERENCE_KEY = "omniai.default_model_id";

export function getPreferredModelId(): string {
  if (typeof window === "undefined") return "auto";
  return localStorage.getItem(MODEL_PREFERENCE_KEY) || "auto";
}

export function setPreferredModelId(modelId: string) {
  if (typeof window === "undefined") return;
  localStorage.setItem(MODEL_PREFERENCE_KEY, modelId);
}
