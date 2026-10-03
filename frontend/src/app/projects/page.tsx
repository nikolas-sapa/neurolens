"use client";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { ArrowLeft, Trash2, ExternalLink, FolderOpen } from "lucide-react";
import { listProjects, getProject, deleteProject } from "@/lib/api";
import type { ProjectSummary } from "@/types/analysis";

function typeLabel(t: string) {
  const map: Record<string, string> = { text: "Text", image: "Image", video: "Video", youtube: "YouTube", pdf: "PDF" };
  return map[t] ?? t;
}

function timeAgo(iso: string) {
  const diff = Date.now() - new Date(iso + "Z").getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function ProjectsPage() {
  const router = useRouter();
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listProjects()
      .then(setProjects)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  async function openProject(id: number) {
    try {
      const project = await getProject(id);
      sessionStorage.setItem("np_result", JSON.stringify(project.result));
      router.push("/analysis");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load project");
    }
  }

  async function handleDelete(id: number, e: React.MouseEvent) {
    e.stopPropagation();
    setError(null);
    try {
      await deleteProject(id);
      setProjects((p) => p.filter((x) => x.id !== id));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to delete project");
    }
  }

  return (
    <main className="min-h-screen px-4 py-10 max-w-3xl mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <Button variant="ghost" size="sm" onClick={() => router.push("/")}>
          <ArrowLeft className="w-4 h-4 mr-1" /> Back
        </Button>
        <div className="flex items-center gap-2">
          <FolderOpen className="w-5 h-5 text-muted-foreground" />
          <h1 className="text-2xl font-bold">Projects</h1>
        </div>
      </div>

      {loading && <p className="text-sm text-muted-foreground">Loading…</p>}
      {error && <p className="text-sm text-rose-500">{error}</p>}

      {!loading && projects.length === 0 && (
        <div className="text-center py-20 text-muted-foreground">
          <FolderOpen className="w-10 h-10 mx-auto mb-3 opacity-30" />
          <p className="text-sm">No saved projects yet.</p>
          <p className="text-xs mt-1">Run an analysis and click Save to get started.</p>
        </div>
      )}

      <div className="space-y-2">
        {projects.map((p) => (
          <div
            key={p.id}
            onClick={() => openProject(p.id)}
            className="flex items-center gap-4 px-4 py-3 rounded-xl border border-border bg-card hover:bg-accent/40 cursor-pointer transition-colors group"
          >
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm truncate">{p.name}</p>
              <p className="text-xs text-muted-foreground mt-0.5">
                {typeLabel(p.type)} · {timeAgo(p.created_at)}
              </p>
            </div>
            <ExternalLink className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
            <button
              onClick={(e) => handleDelete(p.id, e)}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-950/30 transition-colors shrink-0"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </main>
  );
}
