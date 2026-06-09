import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  generateBrief,
  getStory,
  updateBrief,
  type StoryBrief,
} from "@/lib/stories";

export const Route = createFileRoute("/stories/$storyId")({
  component: StoryPage,
});

const LEVEL_LABELS: Record<keyof StoryBrief["levels"], string> = {
  just_starting: "Just Starting",
  beginner: "Beginner",
  intermediate: "Intermediate",
  advanced: "Advanced",
};

function StoryPage() {
  const { storyId } = Route.useParams();
  const id = Number(storyId);
  const qc = useQueryClient();

  const story = useQuery({
    queryKey: ["story", id],
    queryFn: () => getStory(id),
  });

  // Bumped on each regenerate so the editor remounts and re-seeds from the new brief.
  const [briefKey, setBriefKey] = useState(0);

  // Keep the cached story in sync after generate/save (no refetch needed).
  const syncBrief = (brief: StoryBrief) =>
    qc.setQueryData(["story", id], (old: typeof story.data) =>
      old ? { ...old, brief } : old,
    );

  const generate = useMutation({
    mutationFn: () => generateBrief(id),
    onSuccess: (brief) => {
      syncBrief(brief);
      setBriefKey((k) => k + 1);
    },
  });
  const save = useMutation({
    mutationFn: (brief: StoryBrief) => updateBrief(id, brief),
    onSuccess: syncBrief,
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

  const { topic_text, status, sources, brief } = story.data;

  return (
    <main className="mx-auto max-w-3xl px-6 py-12">
      <Link
        to="/"
        search={{ topic: topic_text }}
        className="text-sm text-muted-foreground hover:underline"
      >
        ← Back to research
      </Link>
      <p className="mt-4 text-sm text-muted-foreground">Draft · {status}</p>
      <h1 className="mt-1 text-3xl font-bold tracking-tight">{topic_text}</h1>

      {/* Brief */}
      <section className="mt-8">
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-semibold">Brief</h2>
          {brief && (
            <Button
              variant="outline"
              onClick={() => generate.mutate()}
              disabled={generate.isPending}
            >
              {generate.isPending ? "Regenerating…" : "Regenerate"}
            </Button>
          )}
        </div>

        {generate.isError && (
          <p className="mt-2 text-sm text-destructive">
            {(generate.error as Error).message}
          </p>
        )}

        {!brief ? (
          <div className="mt-3">
            <p className="text-base text-muted-foreground">
              Generate a brief from the selected sources. This extracts their full
              text and can take ~30–60s.
            </p>
            <Button
              className="mt-4 h-11 text-base"
              onClick={() => generate.mutate()}
              disabled={generate.isPending}
            >
              {generate.isPending ? "Generating brief…" : "Generate brief"}
            </Button>
          </div>
        ) : (
          <BriefEditor
            key={briefKey}
            initialBrief={brief}
            onSave={(b) => save.mutate(b)}
            saving={save.isPending}
            saved={save.isSuccess}
            saveError={save.isError ? (save.error as Error).message : null}
          />
        )}
      </section>

      {/* Sources */}
      <section className="mt-10">
        <h2 className="text-xl font-semibold">
          Sources{" "}
          <span className="text-muted-foreground">({sources.length})</span>
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
      </section>
    </main>
  );
}

function BriefEditor({
  initialBrief,
  onSave,
  saving,
  saved,
  saveError,
}: {
  initialBrief: StoryBrief;
  onSave: (brief: StoryBrief) => void;
  saving: boolean;
  saved: boolean;
  saveError: string | null;
}) {
  const [draft, setDraft] = useState<StoryBrief>(initialBrief);

  return (
    <div className="mt-4 space-y-5">
      <Field
        label="Overview"
        value={draft.overview}
        rows={8}
        onChange={(v) => setDraft({ ...draft, overview: v })}
      />
      <Field
        label="Angle"
        value={draft.angle}
        rows={4}
        onChange={(v) => setDraft({ ...draft, angle: v })}
      />
      <Field
        label="Spine"
        value={draft.spine}
        rows={3}
        onChange={(v) => setDraft({ ...draft, spine: v })}
      />
      <div>
        <h3 className="text-base font-semibold">Per-level scope</h3>
        <div className="mt-2 space-y-4">
          {(Object.keys(LEVEL_LABELS) as (keyof StoryBrief["levels"])[]).map(
            (key) => (
              <Field
                key={key}
                label={LEVEL_LABELS[key]}
                value={draft.levels[key]}
                rows={3}
                onChange={(v) =>
                  setDraft({ ...draft, levels: { ...draft.levels, [key]: v } })
                }
              />
            ),
          )}
        </div>
      </div>

      <div className="flex items-center gap-3">
        <Button
          className="h-11 text-base"
          onClick={() => onSave(draft)}
          disabled={saving}
        >
          {saving ? "Saving…" : "Save brief"}
        </Button>
        {saved && !saving && (
          <span className="text-sm text-muted-foreground">Saved</span>
        )}
        {saveError && <span className="text-sm text-destructive">{saveError}</span>}
      </div>

      <p className="border-t pt-4 text-base text-muted-foreground">
        Next: generate the first level from this brief. (Phase 4)
      </p>
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  rows = 4,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  rows?: number;
}) {
  return (
    <div>
      <label className="text-base font-medium">{label}</label>
      <Textarea
        value={value}
        rows={rows}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 text-base"
      />
    </div>
  );
}
