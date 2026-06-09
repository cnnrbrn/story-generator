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

// Mirrors backend app/schemas/story.py items
export interface VocabItem {
  word: string;
  translation: string;
}

export interface VerbItem {
  surface_form: string;
  lemma: string;
  tense: string;
  mood: string;
  translation: string;
  example_sentence_target: string;
  example_sentence_en: string;
}

export interface GrammarItem {
  surface_form: string;
  lemma: string;
  tense: string;
  mood: string;
  translation: string;
}

// The generator's structured output for one level (also the PUT body).
export interface StoryLevelOutput {
  level: string;
  title_target: string;
  title_en: string | null;
  summary_en: string | null;
  story_text: string;
  vocab: VocabItem[];
  verbs: VerbItem[];
  grammar: GrammarItem[];
}

// A saved level as returned by GET (adds status/version; fields may be null).
export interface LevelOut {
  level: string;
  title_target: string | null;
  title_en: string | null;
  summary_en: string | null;
  story_text: string | null;
  status: string;
  version: number;
  vocab: VocabItem[];
  verbs: VerbItem[];
  grammar: GrammarItem[];
}

export interface StoryDetail {
  id: number;
  topic_text: string;
  language_code: string;
  status: string;
  brief: StoryBrief | null;
  brief_prompt: PromptPreview | null;
  sources: SourceOut[];
  levels: LevelOut[];
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

// The exact prompt sent to the model, for display in the UI.
export interface PromptPreview {
  system: string;
  user: string;
}

export interface BriefResponse {
  brief: StoryBrief;
  prompt: PromptPreview;
}

// Generate the brief from the story's saved sources (extract + LLM). Slow (~30-60s).
export function generateBrief(id: number): Promise<BriefResponse> {
  return apiFetch<BriefResponse>(`/api/stories/${id}/brief`, { method: "POST" });
}

// Save the creator's edited brief.
export function updateBrief(id: number, brief: StoryBrief): Promise<StoryBrief> {
  return apiFetch<StoryBrief>(`/api/stories/${id}/brief`, {
    method: "PUT",
    body: JSON.stringify(brief),
  });
}

export interface GenerateLevelResponse {
  level: StoryLevelOutput;
  issues: string[];
  passed: boolean;
  attempts: number;
  prompt: PromptPreview;
}

export interface SaveLevelResponse {
  issues: string[];
  passed: boolean;
}

// Generate a draft for one level (brief + sources + prior levels). Slow (~30-90s).
export function generateLevel(
  id: number,
  level: string,
): Promise<GenerateLevelResponse> {
  return apiFetch<GenerateLevelResponse>(
    `/api/stories/${id}/levels/${level}/generate`,
    { method: "POST" },
  );
}

// Save the creator's edited level.
export function saveLevel(
  id: number,
  level: string,
  body: StoryLevelOutput,
): Promise<SaveLevelResponse> {
  return apiFetch<SaveLevelResponse>(`/api/stories/${id}/levels/${level}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}
