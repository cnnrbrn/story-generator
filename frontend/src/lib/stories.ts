import { apiFetch } from "@/lib/api";
import type { SourceItem } from "@/lib/research";

// Mirrors backend app/routers/stories.py : CreateStoryRequest
export interface CreateStoryRequest {
  topic: string;
  language_code?: string;
  sources: SourceItem[];
  pasted_text: string;
}

// Mirrors SourceOut / StoryDetail in app/routers/stories.py
export interface SourceOut {
  id: number;
  type: string;
  title: string | null;
  url: string | null;
  citation_text: string | null;
}

export interface StoryDetail {
  id: number;
  topic_text: string;
  language_code: string;
  status: string;
  brief: Record<string, unknown> | null;
  sources: SourceOut[];
}

export function createStory(body: CreateStoryRequest): Promise<{ id: number }> {
  return apiFetch<{ id: number }>("/api/stories", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getStory(id: number): Promise<StoryDetail> {
  return apiFetch<StoryDetail>(`/api/stories/${id}`);
}
