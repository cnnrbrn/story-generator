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

// Mirrors backend app/schemas/brief.py
export interface LevelScopes {
  just_starting: string;
  beginner: string;
  intermediate: string;
  advanced: string;
}

export interface StoryBrief {
  overview: string;
  angle: string;
  spine: string;
  levels: LevelScopes;
}

export interface StoryDetail {
  id: number;
  topic_text: string;
  language_code: string;
  status: string;
  brief: StoryBrief | null;
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

// Generate the brief from the story's saved sources (extract + LLM). Slow (~30-60s).
export function generateBrief(id: number): Promise<StoryBrief> {
  return apiFetch<StoryBrief>(`/api/stories/${id}/brief`, { method: "POST" });
}

// Save the creator's edited brief.
export function updateBrief(id: number, brief: StoryBrief): Promise<StoryBrief> {
  return apiFetch<StoryBrief>(`/api/stories/${id}/brief`, {
    method: "PUT",
    body: JSON.stringify(brief),
  });
}
