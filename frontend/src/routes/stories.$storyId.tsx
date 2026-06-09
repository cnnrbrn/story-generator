import { createFileRoute } from "@tanstack/react-router";
import { useQuery } from "@tanstack/react-query";
import { getStory } from "@/lib/stories";

export const Route = createFileRoute("/stories/$storyId")({
  component: StoryPage,
});

function StoryPage() {
  const { storyId } = Route.useParams();
  const id = Number(storyId);

  const story = useQuery({
    queryKey: ["story", id],
    queryFn: () => getStory(id),
  });

  if (story.isPending) {
    return <main className="mx-auto max-w-3xl px-6 py-12">Loading…</main>;
  }
  if (story.isError) {
    return (
      <main className="mx-auto max-w-3xl px-6 py-12 text-destructive">
        {(story.error as Error).message}
      </main>
    );
  }

  const { topic_text, status, sources } = story.data;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <p className="text-sm text-muted-foreground">Draft · {status}</p>
      <h1 className="mt-1 text-3xl font-bold tracking-tight">{topic_text}</h1>

      <h2 className="mt-8 text-xl font-semibold">
        Sources <span className="text-muted-foreground">({sources.length})</span>
      </h2>
      <ul className="mt-3 space-y-2">
        {sources.map((s) => (
          <li key={s.id} className="rounded-md border p-4">
            <p className="text-lg font-medium">
              {s.title || s.url || "(untitled)"}
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                {s.type}
              </span>
            </p>
            {s.url && (
              <p className="truncate text-sm text-muted-foreground">{s.url}</p>
            )}
            {s.citation_text && (
              <p className="mt-1 line-clamp-3 text-base text-muted-foreground">
                {s.citation_text}
              </p>
            )}
          </li>
        ))}
      </ul>

      <p className="mt-8 text-base text-muted-foreground">
        Next: generate the brief from these sources. (Phase 3)
      </p>
    </main>
  );
}
