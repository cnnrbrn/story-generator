import { useState } from "react";
import { createFileRoute, Link } from "@tanstack/react-router";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import {
  generateBrief,
  generateLevel,
  getStory,
  saveLevel,
  updateBrief,
  type LevelOut,
  type PromptPreview,
  type StoryBrief,
  type StoryLevelOutput,
  type VerbItem,
  type VocabItem,
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
  // The exact prompt last sent to the model (shown after generating; not persisted).
  const [prompt, setPrompt] = useState<PromptPreview | null>(null);

  // Keep the cached story in sync after generate/save (no refetch needed).
  const syncBrief = (brief: StoryBrief) =>
    qc.setQueryData(["story", id], (old: typeof story.data) =>
      old ? { ...old, brief } : old,
    );

  const generate = useMutation({
    mutationFn: () => generateBrief(id),
    onSuccess: ({ brief, prompt }) => {
      syncBrief(brief);
      setBriefKey((k) => k + 1);
      setPrompt(prompt);
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

  const { topic_text, status, sources, brief, brief_prompt } = story.data;

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

        {(prompt ?? brief_prompt) && (
          <PromptPanel prompt={(prompt ?? brief_prompt)!} />
        )}
      </section>

      {/* Levels (4c-i: just_starting only) */}
      {brief && (
        <section className="mt-10">
          <h2 className="text-xl font-semibold">Levels</h2>
          <LevelSection
            storyId={id}
            levelKey="just_starting"
            label="Just Starting"
            saved={story.data.levels.find((l) => l.level === "just_starting")}
          />
        </section>
      )}

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

function levelOutToDraft(l: LevelOut): StoryLevelOutput {
  return {
    level: l.level,
    title_target: l.title_target ?? "",
    title_en: l.title_en,
    summary_en: l.summary_en,
    story_text: l.story_text ?? "",
    vocab: l.vocab,
    verbs: l.verbs,
    grammar: l.grammar,
  };
}

function LevelSection({
  storyId,
  levelKey,
  label,
  saved,
}: {
  storyId: number;
  levelKey: string;
  label: string;
  saved: LevelOut | undefined;
}) {
  const qc = useQueryClient();
  const [draft, setDraft] = useState<StoryLevelOutput | null>(
    saved ? levelOutToDraft(saved) : null,
  );
  const [prompt, setPrompt] = useState<PromptPreview | null>(null);
  const [issues, setIssues] = useState<string[] | null>(null);

  const generate = useMutation({
    mutationFn: () => generateLevel(storyId, levelKey),
    onSuccess: (res) => {
      setDraft(res.level);
      setPrompt(res.prompt);
      setIssues(res.issues);
    },
  });
  const save = useMutation({
    mutationFn: (body: StoryLevelOutput) => saveLevel(storyId, levelKey, body),
    onSuccess: (res) => {
      setIssues(res.issues);
      qc.invalidateQueries({ queryKey: ["story", storyId] });
    },
  });

  return (
    <div className="mt-4 rounded-md border p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold">
          {label}
          {saved && (
            <span className="ml-2 text-sm font-normal text-muted-foreground">
              saved · v{saved.version}
            </span>
          )}
        </h3>
        {draft && (
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

      {!draft ? (
        <Button
          className="mt-3 h-11 text-base"
          onClick={() => generate.mutate()}
          disabled={generate.isPending}
        >
          {generate.isPending ? "Generating…" : `Generate ${label}`}
        </Button>
      ) : (
        <div className="mt-4 space-y-5">
          <Field
            label="Title (target)"
            value={draft.title_target}
            rows={1}
            onChange={(v) => setDraft({ ...draft, title_target: v })}
          />
          <Field
            label="Title (English)"
            value={draft.title_en ?? ""}
            rows={1}
            onChange={(v) => setDraft({ ...draft, title_en: v })}
          />
          <Field
            label="Summary (English)"
            value={draft.summary_en ?? ""}
            rows={2}
            onChange={(v) => setDraft({ ...draft, summary_en: v })}
          />
          <Field
            label="Story"
            value={draft.story_text}
            rows={10}
            onChange={(v) => setDraft({ ...draft, story_text: v })}
          />

          <VocabRows
            vocab={draft.vocab}
            onChange={(vocab) => setDraft({ ...draft, vocab })}
          />
          <VerbRows
            verbs={draft.verbs}
            onChange={(verbs) => setDraft({ ...draft, verbs })}
          />

          {issues && (
            <div className="rounded bg-muted p-3 text-sm">
              {issues.length === 0 ? (
                <span className="text-muted-foreground">No validator issues.</span>
              ) : (
                <>
                  <p className="font-medium">Validator flags (advisory):</p>
                  <ul className="mt-1 list-disc pl-5 text-muted-foreground">
                    {issues.map((it, i) => (
                      <li key={i}>{it}</li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          )}

          <div className="flex items-center gap-3">
            <Button
              className="h-11 text-base"
              onClick={() => save.mutate(draft)}
              disabled={save.isPending}
            >
              {save.isPending ? "Saving…" : "Save level"}
            </Button>
            {save.isSuccess && !save.isPending && (
              <span className="text-sm text-muted-foreground">Saved</span>
            )}
            {save.isError && (
              <span className="text-sm text-destructive">
                {(save.error as Error).message}
              </span>
            )}
          </div>

          {prompt && <PromptPanel prompt={prompt} />}
        </div>
      )}
    </div>
  );
}

function VocabRows({
  vocab,
  onChange,
}: {
  vocab: VocabItem[];
  onChange: (v: VocabItem[]) => void;
}) {
  const update = (i: number, patch: Partial<VocabItem>) =>
    onChange(vocab.map((v, idx) => (idx === i ? { ...v, ...patch } : v)));
  const remove = (i: number) => onChange(vocab.filter((_, idx) => idx !== i));
  const add = () => onChange([...vocab, { word: "", translation: "" }]);

  return (
    <div>
      <h4 className="text-base font-semibold">Vocabulary ({vocab.length})</h4>
      <div className="mt-2 space-y-2">
        {vocab.map((v, i) => (
          <div key={i} className="flex gap-2">
            <Input
              value={v.word}
              placeholder="word"
              onChange={(e) => update(i, { word: e.target.value })}
            />
            <Input
              value={v.translation}
              placeholder="translation"
              onChange={(e) => update(i, { translation: e.target.value })}
            />
            <Button variant="outline" onClick={() => remove(i)} aria-label="Remove">
              ✕
            </Button>
          </div>
        ))}
      </div>
      <Button variant="outline" className="mt-2" onClick={add}>
        + Add word
      </Button>
    </div>
  );
}

function VerbRows({
  verbs,
  onChange,
}: {
  verbs: VerbItem[];
  onChange: (v: VerbItem[]) => void;
}) {
  const update = (i: number, patch: Partial<VerbItem>) =>
    onChange(verbs.map((v, idx) => (idx === i ? { ...v, ...patch } : v)));
  const remove = (i: number) => onChange(verbs.filter((_, idx) => idx !== i));
  const add = () =>
    onChange([
      ...verbs,
      {
        surface_form: "",
        lemma: "",
        tense: "",
        mood: "",
        translation: "",
        example_sentence_target: "",
        example_sentence_en: "",
      },
    ]);

  return (
    <div>
      <h4 className="text-base font-semibold">Verbs ({verbs.length})</h4>
      <div className="mt-2 space-y-3">
        {verbs.map((v, i) => (
          <div key={i} className="space-y-2 rounded border p-3">
            <div className="flex gap-2">
              <Input
                value={v.surface_form}
                placeholder="surface form"
                onChange={(e) => update(i, { surface_form: e.target.value })}
              />
              <Input
                value={v.lemma}
                placeholder="lemma"
                onChange={(e) => update(i, { lemma: e.target.value })}
              />
              <Input
                value={v.tense}
                placeholder="tense"
                onChange={(e) => update(i, { tense: e.target.value })}
              />
              <Input
                value={v.mood}
                placeholder="mood"
                onChange={(e) => update(i, { mood: e.target.value })}
              />
              <Button
                variant="outline"
                onClick={() => remove(i)}
                aria-label="Remove"
              >
                ✕
              </Button>
            </div>
            <Input
              value={v.translation}
              placeholder="translation"
              onChange={(e) => update(i, { translation: e.target.value })}
            />
            <Input
              value={v.example_sentence_target}
              placeholder="example (target language)"
              onChange={(e) =>
                update(i, { example_sentence_target: e.target.value })
              }
            />
            <Input
              value={v.example_sentence_en}
              placeholder="example (English)"
              onChange={(e) => update(i, { example_sentence_en: e.target.value })}
            />
          </div>
        ))}
      </div>
      <Button variant="outline" className="mt-2" onClick={add}>
        + Add verb
      </Button>
    </div>
  );
}

function PromptPanel({ prompt }: { prompt: PromptPreview }) {
  return (
    <details className="mt-5 rounded-md border p-4">
      <summary className="cursor-pointer text-sm font-medium text-muted-foreground">
        Prompt sent to the model
      </summary>
      <div className="mt-3 space-y-4">
        <div>
          <p className="text-xs font-semibold uppercase text-muted-foreground">
            System
          </p>
          <pre className="mt-1 max-h-80 overflow-auto rounded bg-muted p-3 text-xs whitespace-pre-wrap">
            {prompt.system}
          </pre>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase text-muted-foreground">
            User
          </p>
          <pre className="mt-1 max-h-96 overflow-auto rounded bg-muted p-3 text-xs whitespace-pre-wrap">
            {prompt.user}
          </pre>
        </div>
      </div>
    </details>
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
