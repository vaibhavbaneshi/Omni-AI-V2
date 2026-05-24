import { useCallback, useEffect, useState } from "react";
import {
  createMemory,
  deleteMemory,
  listMemories,
  type MemoryRecord,
} from "@/lib/api";

export function useMemory(token?: string | null) {
  const [memories, setMemories] = useState<MemoryRecord[]>([]);

  const refreshMemories = useCallback(async () => {
    if (!token) return;
    const result = await listMemories(token);
    setMemories(result.memories);
  }, [token]);

  useEffect(() => {
    const id = window.setTimeout(() => {
      refreshMemories().catch(() => undefined);
    }, 0);

    return () => window.clearTimeout(id);
  }, [refreshMemories]);

  const addMemory = async (content: string, category = "preference") => {
    const memory = await createMemory(content, token, { category });
    await refreshMemories();
    return memory;
  };

  const removeMemory = async (memoryId: number) => {
    await deleteMemory(memoryId, token);
    await refreshMemories();
  };

  return {
    memories,
    refreshMemories,
    addMemory,
    removeMemory,
  };
}
