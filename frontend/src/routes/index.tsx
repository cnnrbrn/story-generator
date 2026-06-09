import { useState } from "react";
import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import { postResearch, type SourceItem } from "@/lib/research";

export const Route = createFileRoute("/")({
  // The searched topic is kept in the URL (?topic=…) so a reload restores it.
  validateSearch: (search: Record<string, unknown>): { topic?: string } => ({
    topic: typeof search.topic === "string" ? search.topic : undefined,
  }),
  component: Research,
});

function Research() {
  // The searched topic comes from the URL, so a reload restores it. It drives the
  // query cache key, so the same topic returns cached results (no re-billing).
  const { topic: submittedTopic = "" } = Route.useSearch();
  const navigate = useNavigate({ from: Route.fullPath });
  // The text box value; seeded from the URL on first load.
  const [topic, setTopic] = useState(submittedTopic);
  // Selected source URLs. A Set gives O(1) add/remove/has.
  const [selected, setSelected] = useState<Set<string>>(new Set());
  // Freeform content the user pastes in (full articles snippets can't capture).
  const [pasted, setPasted] = useState("");

  const research = useQuery({
    queryKey: ["research", submittedTopic],
    queryFn: () => postResearch(submittedTopic),
    enabled: submittedTopic.length > 0, // don't run until a topic is submitted
    staleTime: Infinity, // results are stable; never auto-refetch
    refetchOnWindowFocus: false, // don't re-bill the API on tab focus
  });

  const sources = research.data?.sources ?? [];

  function toggle(url: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(url)) next.delete(url);
      else next.add(url);
      return next;
    });
  }

  function onSearch(e: React.SubmitEvent) {
    e.preventDefault();
    const trimmed = topic.trim();
    if (!trimmed) return;
    setSelected(new Set()); // clear prior selection for the new search
    navigate({ search: { topic: trimmed } }); // URL drives/keys the query
  }

  function onStartBrief() {
    // Phase 2/3 will POST these to create a draft Story + generate the brief.
    const payload = {
      topic: topic.trim(),
      sources: sources.filter((s) => selected.has(s.url)),
      pasted_text: pasted.trim(),
    };
    console.log("start brief (stub):", payload);
  }

  const canStart = selected.size > 0 || pasted.trim().length > 0;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <h1 className="text-4xl font-bold tracking-tight">Story Generator</h1>

      <form onSubmit={onSearch} className="mt-6 flex gap-2">
        <Input
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="e.g. the fall of Tenochtitlan"
          aria-label="Topic"
          className="h-11 text-base"
        />
        <Button
          type="submit"
          disabled={research.isFetching || !topic.trim()}
          className="h-11 text-base"
        >
          {research.isFetching ? "Researching…" : "Research"}
        </Button>
      </form>

      {research.isError && (
        <p className="mt-4 text-sm text-destructive">
          {(research.error as Error).message}
        </p>
      )}

      {research.isFetching && (
        <p className="mt-8 text-base text-muted-foreground">
          Planning searches and querying the web...
        </p>
      )}

      {research.isSuccess && sources.length === 0 && (
        <p className="mt-8 text-base text-muted-foreground">
          No sources found.
        </p>
      )}

      {sources.length > 0 && (
        <>
          <div className="mt-8 flex items-baseline justify-between">
            <h2 className="text-xl font-semibold">Sources</h2>
            <span className="text-base text-muted-foreground">
              {selected.size} of {sources.length} selected
            </span>
          </div>
          <ul className="mt-3 space-y-2">
            {sources.map((s) => (
              <SourceRow
                key={s.url}
                source={s}
                checked={selected.has(s.url)}
                onToggle={() => toggle(s.url)}
              />
            ))}
          </ul>

          <div className="mt-8">
            <label htmlFor="pasted" className="text-base font-medium">
              Paste extra content (optional)
            </label>
            <p className="mb-2 text-base text-muted-foreground">
              Anything to include verbatim — a full article, notes, a primary
              source.
            </p>
            <Textarea
              id="pasted"
              value={pasted}
              onChange={(e) => setPasted(e.target.value)}
              placeholder="Paste content here…"
              className="min-h-40 text-base"
            />
          </div>

          <div className="mt-6 flex justify-end">
            <Button
              onClick={onStartBrief}
              disabled={!canStart}
              className="h-11 text-base"
            >
              Start brief
            </Button>
          </div>
        </>
      )}
    </main>
  );
}

function SourceRow({
  source,
  checked,
  onToggle,
}: {
  source: SourceItem;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <li className="flex gap-4 rounded-md border p-4">
      <Checkbox
        checked={checked}
        onCheckedChange={onToggle}
        className="mt-1"
        aria-label={`Select ${source.title || source.url}`}
      />
      <div className="min-w-0">
        <a
          href={source.url}
          target="_blank"
          rel="noreferrer"
          className="text-lg font-medium hover:underline"
        >
          {source.title || source.url}
        </a>
        <p className="truncate text-base font-semibold text-muted-foreground">
          {source.url}
        </p>
        {source.snippet && (
          <p className="mt-1 line-clamp-3 text-base text-muted-foreground">
            {source.snippet}
          </p>
        )}
      </div>
    </li>
  );
}
