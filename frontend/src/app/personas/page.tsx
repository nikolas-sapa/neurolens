"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Plus, Pencil, Trash2, Users, Sparkles, Loader2, X } from "lucide-react";
import { listPersonas, getPersona, createPersona, updatePersona, deletePersona, generatePersona } from "@/lib/api";
import type { PersonaSummary } from "@/types/analysis";

const REGIONS = [
  { key: "visual_cortex", label: "Visual Cortex" },
  { key: "face_social", label: "Face & Social" },
  { key: "amygdala", label: "Amygdala (Emotion)" },
  { key: "hippocampus", label: "Hippocampus (Memory)" },
  { key: "language_areas", label: "Language Areas" },
  { key: "reward_circuit", label: "Reward Circuit" },
  { key: "prefrontal", label: "Prefrontal (Logic)" },
  { key: "motor_action", label: "Motor Action" },
];

type FormState = {
  key: string;
  name: string;
  tagline: string;
  overlays: Record<string, string>;
};

function overlaysToSteps(overlays: Record<string, string>): Record<string, string[]> {
  const result: Record<string, string[]> = {};
  for (const [k, v] of Object.entries(overlays)) {
    const steps = v.split("\n").map((s) => s.trim()).filter(Boolean);
    if (steps.length > 0) result[k] = steps;
  }
  return result;
}

function stepsToOverlays(step_overlays: Record<string, string[]>): Record<string, string> {
  const result: Record<string, string> = {};
  for (const [k, v] of Object.entries(step_overlays)) {
    result[k] = v.join("\n");
  }
  return result;
}

const emptyForm = (): FormState => ({
  key: "",
  name: "",
  tagline: "",
  overlays: Object.fromEntries(REGIONS.map((r) => [r.key, ""])),
});

export default function PersonasPage() {
  const router = useRouter();
  const [personas, setPersonas] = useState<PersonaSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState<number | "new" | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm());
  const [saving, setSaving] = useState(false);
  const [genOpen, setGenOpen] = useState(false);
  const [genName, setGenName] = useState("");
  const [genSource, setGenSource] = useState("");
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState<string | null>(null);

  useEffect(() => {
    listPersonas()
      .then(setPersonas)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function startEdit(id: number) {
    try {
      const p = await getPersona(id);
      setForm({
        key: p.key,
        name: p.name,
        tagline: p.tagline,
        overlays: { ...Object.fromEntries(REGIONS.map((r) => [r.key, ""])), ...stepsToOverlays(p.step_overlays) },
      });
      setEditing(id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load");
    }
  }

  function startNew() {
    setForm(emptyForm());
    setEditing("new");
  }

  function cancelEdit() {
    setEditing(null);
  }

  async function handleSave() {
    if (!form.key.trim() || !form.name.trim()) {
      setError("Key and name are required.");
      return;
    }
    setSaving(true);
    setError(null);
    const data = {
      key: form.key.trim(),
      name: form.name.trim(),
      tagline: form.tagline.trim(),
      step_overlays: overlaysToSteps(form.overlays),
    };
    try {
      if (editing === "new") {
        const { id } = await createPersona(data);
        setPersonas((prev) => [...prev, { id, key: data.key, name: data.name, tagline: data.tagline }]);
      } else if (typeof editing === "number") {
        await updatePersona(editing, data);
        setPersonas((prev) =>
          prev.map((p) => (p.id === editing ? { ...p, key: data.key, name: data.name, tagline: data.tagline } : p))
        );
      }
      setEditing(null);
      setForm(emptyForm());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  function openGenerator() {
    setGenName("");
    setGenSource("");
    setGenError(null);
    setGenOpen(true);
  }

  function closeGenerator() {
    setGenOpen(false);
    setGenError(null);
  }

  async function handleGenerate() {
    if (!genName.trim() || genSource.trim().length < 50) {
      setGenError("Provide a creator name and at least a paragraph of their content.");
      return;
    }
    setGenerating(true);
    setGenError(null);
    try {
      const draft = await generatePersona(genName.trim(), genSource.trim());
      const slug = genName.trim().toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9-]/g, "");
      setForm({
        key: slug,
        name: draft.name,
        tagline: draft.tagline,
        overlays: {
          ...Object.fromEntries(REGIONS.map((r) => [r.key, ""])),
          ...stepsToOverlays(draft.step_overlays),
        },
      });
      setEditing("new");
      setGenOpen(false);
    } catch (e) {
      setGenError(e instanceof Error ? e.message : "Generation failed");
    } finally {
      setGenerating(false);
    }
  }

  async function handleDelete(id: number, e: React.MouseEvent) {
    e.stopPropagation();
    if (!window.confirm("Delete this persona? This cannot be undone.")) return;
    try {
      await deletePersona(id);
      setPersonas((prev) => prev.filter((p) => p.id !== id));
      if (editing === id) setEditing(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Delete failed");
    }
  }

  return (
    <main className="min-h-screen px-4 py-10 max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <Button variant="ghost" size="sm" onClick={() => router.push("/")}>
          <ArrowLeft className="w-4 h-4 mr-1" /> Back
        </Button>
        <div className="flex items-center gap-2 flex-1">
          <Users className="w-5 h-5 text-muted-foreground" />
          <h1 className="text-2xl font-bold">Creator Personas</h1>
        </div>
        {editing === null && (
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={openGenerator}>
              <Sparkles className="w-4 h-4 mr-1" /> Generate from text
            </Button>
            <Button size="sm" onClick={startNew}>
              <Plus className="w-4 h-4 mr-1" /> New Persona
            </Button>
          </div>
        )}
      </div>

      {error && <p className="text-sm text-rose-500 mb-4">{error}</p>}

      {editing !== null && (
        <div className="border border-border rounded-xl p-5 mb-6 bg-card">
          <h2 className="text-sm font-semibold mb-4">{editing === "new" ? "New Persona" : "Edit Persona"}</h2>
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div>
              <label className="text-xs text-muted-foreground block mb-1">Key (slug)</label>
              <input
                type="text"
                value={form.key}
                onChange={(e) => setForm((f) => ({ ...f, key: e.target.value.toLowerCase().replace(/\s+/g, "-") }))}
                placeholder="e.g. my-creator"
                className="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground block mb-1">Display Name</label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                placeholder="e.g. Alex Hormozi"
                className="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary"
              />
            </div>
          </div>
          <div className="mb-5">
            <label className="text-xs text-muted-foreground block mb-1">Tagline</label>
            <input
              type="text"
              value={form.tagline}
              onChange={(e) => setForm((f) => ({ ...f, tagline: e.target.value }))}
              placeholder="e.g. Direct response. Quantify everything."
              className="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary"
            />
          </div>

          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-3">
            Brain Region Steps — one per line, leave blank to skip a region
          </p>
          <div className="space-y-3">
            {REGIONS.map((region) => (
              <div key={region.key}>
                <label className="text-xs text-muted-foreground block mb-1">{region.label}</label>
                <textarea
                  value={form.overlays[region.key] ?? ""}
                  onChange={(e) =>
                    setForm((f) => ({ ...f, overlays: { ...f.overlays, [region.key]: e.target.value } }))
                  }
                  rows={2}
                  placeholder={`Steps for ${region.label}…`}
                  className="w-full px-3 py-2 text-sm border rounded-lg bg-background resize-none focus:outline-none focus:ring-2 focus:ring-primary"
                />
              </div>
            ))}
          </div>

          <div className="flex gap-2 mt-5">
            <Button size="sm" disabled={saving} onClick={handleSave}>
              {saving ? "Saving…" : editing === "new" ? "Create" : "Save changes"}
            </Button>
            <Button variant="ghost" size="sm" onClick={cancelEdit}>
              Cancel
            </Button>
          </div>
        </div>
      )}

      {loading && <p className="text-sm text-muted-foreground">Loading…</p>}

      {!loading && personas.length === 0 && (
        <div className="text-center py-20 text-muted-foreground">
          <Users className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">No personas yet.</p>
        </div>
      )}

      <div className="space-y-2">
        {personas.map((p) => (
          <div
            key={p.id}
            className="flex items-center gap-4 px-4 py-3 rounded-xl border border-border bg-card transition-colors"
          >
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <p className="font-medium text-sm truncate">{p.name}</p>
                <span className="text-xs text-muted-foreground border border-border rounded px-1.5 py-0.5 shrink-0">
                  {p.key}
                </span>
              </div>
              {p.tagline && <p className="text-xs text-muted-foreground mt-0.5 truncate">{p.tagline}</p>}
            </div>
            <button
              onClick={() => startEdit(p.id)}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-accent transition-colors shrink-0"
            >
              <Pencil className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={(e) => handleDelete(p.id, e)}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors shrink-0"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>

      {genOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-background/80 backdrop-blur-sm px-4"
          onClick={(e) => { if (e.target === e.currentTarget && !generating) closeGenerator(); }}
        >
          <div className="w-full max-w-2xl rounded-2xl border border-border bg-card shadow-xl">
            <div className="flex items-center justify-between px-6 py-4 border-b border-border">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-muted-foreground" />
                <h2 className="text-sm font-semibold">Generate Persona from Content</h2>
              </div>
              <button
                onClick={closeGenerator}
                disabled={generating}
                className="text-muted-foreground hover:text-foreground transition-colors disabled:opacity-40"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="px-6 py-5 space-y-4">
              <p className="text-xs text-muted-foreground leading-relaxed">
                Paste creator content — book excerpts, video transcripts, tweet threads, or a NotebookLM export.
                The model will extract their tactical playbook and pre-fill the persona form for you to review.
              </p>

              <div>
                <label className="text-xs text-muted-foreground block mb-1.5">Creator name</label>
                <input
                  type="text"
                  value={genName}
                  onChange={(e) => setGenName(e.target.value)}
                  placeholder="e.g. Alex Hormozi"
                  disabled={generating}
                  className="w-full px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-60"
                />
              </div>

              <div>
                <label className="text-xs text-muted-foreground block mb-1.5">
                  Source content
                  <span className="ml-1 opacity-60">({genSource.length.toLocaleString()} chars)</span>
                </label>
                <textarea
                  value={genSource}
                  onChange={(e) => setGenSource(e.target.value)}
                  rows={12}
                  placeholder="Paste book chapters, transcripts, threads, NotebookLM summaries, etc."
                  disabled={generating}
                  className="w-full px-3 py-2 text-sm border rounded-lg bg-background resize-none font-mono focus:outline-none focus:ring-2 focus:ring-primary disabled:opacity-60"
                />
              </div>

              {genError && <p className="text-xs text-rose-500">{genError}</p>}

              <div className="flex items-center justify-end gap-2 pt-2">
                <Button variant="ghost" size="sm" onClick={closeGenerator} disabled={generating}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleGenerate} disabled={generating}>
                  {generating ? (
                    <><Loader2 className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Generating…</>
                  ) : (
                    <><Sparkles className="w-3.5 h-3.5 mr-1.5" /> Generate Persona</>
                  )}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
