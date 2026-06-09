import { useState } from 'react'
import { createFileRoute } from '@tanstack/react-router'
import { useMutation } from '@tanstack/react-query'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { postResearch, type SourceItem } from '@/lib/research'

export const Route = createFileRoute('/')({
  component: Research,
})

const PERSPECTIVES = [
  { key: 'anti_imperialist', label: 'Anti-imperialist' },
  { key: 'mainstream', label: 'Mainstream' },
] as const

function Research() {
  const [topic, setTopic] = useState('')

  // useMutation: an imperative async action (POST) with built-in
  // isPending/error/data state — no manual loading flags needed.
  const research = useMutation({
    mutationFn: (t: string) => postResearch(t),
  })

  const sources = research.data?.sources ?? []

  function onSubmit(e: React.SubmitEvent) {
    e.preventDefault()
    const trimmed = topic.trim()
    if (trimmed) research.mutate(trimmed)
  }

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-3xl font-bold tracking-tight">Story Generator</h1>
      <p className="mt-1 text-muted-foreground">
        Enter a historical topic to research sources before generating a story.
      </p>

      <form onSubmit={onSubmit} className="mt-6 flex gap-2">
        <Input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. the fall of Tenochtitlan"
          aria-label="Topic"
        />
        <Button type="submit" disabled={research.isPending || !topic.trim()}>
          {research.isPending ? 'Researching…' : 'Research'}
        </Button>
      </form>

      {research.isError && (
        <p className="mt-4 text-sm text-destructive">
          {(research.error as Error).message}
        </p>
      )}

      {research.isPending && (
        <p className="mt-8 text-sm text-muted-foreground">
          Planning angled searches and querying the web… this can take 10–20s.
        </p>
      )}

      {research.isSuccess && sources.length === 0 && (
        <p className="mt-8 text-sm text-muted-foreground">No sources found.</p>
      )}

      {sources.length > 0 && (
        <div className="mt-8 space-y-8">
          {PERSPECTIVES.map(({ key, label }) => {
            const group = sources.filter((s) => s.perspective === key)
            if (group.length === 0) return null
            return (
              <section key={key}>
                <h2 className="mb-3 text-lg font-semibold">
                  {label}{' '}
                  <span className="text-muted-foreground">({group.length})</span>
                </h2>
                <div className="space-y-3">
                  {group.map((s) => (
                    <SourceCard key={s.url} source={s} />
                  ))}
                </div>
              </section>
            )
          })}
        </div>
      )}
    </main>
  )
}

function SourceCard({ source }: { source: SourceItem }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">
          <a
            href={source.url}
            target="_blank"
            rel="noreferrer"
            className="hover:underline"
          >
            {source.title || source.url}
          </a>
        </CardTitle>
        <CardDescription className="truncate">{source.url}</CardDescription>
      </CardHeader>
      {source.snippet && (
        <CardContent className="text-sm text-muted-foreground">
          {source.snippet}
        </CardContent>
      )}
    </Card>
  )
}
