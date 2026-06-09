import { apiFetch } from '@/lib/api'

// Mirrors backend app/schemas/source.py : SourceItem
export interface SourceItem {
  title: string
  url: string
  snippet: string
}

// Mirrors backend app/routers/research.py : ResearchResponse
export interface ResearchResponse {
  topic: string
  sources: SourceItem[]
}

export function postResearch(topic: string): Promise<ResearchResponse> {
  return apiFetch<ResearchResponse>('/api/research', {
    method: 'POST',
    body: JSON.stringify({ topic }),
  })
}
