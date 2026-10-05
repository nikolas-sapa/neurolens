"use client";
import { useState, useEffect, useRef } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Upload, Link, FileText, Loader2, X } from "lucide-react";

interface Props {
  onResult: (result: unknown) => void;
  onError: (msg: string) => void;
  label?: string;
  persona?: string;
}

const STAGES = [
  { after: 0,   label: "Sending…" },
  { after: 4,   label: "Processing content…" },
  { after: 15,  label: "Loading AI model (first run takes ~2 min)…" },
  { after: 60,  label: "Model loaded — running analysis…" },
  { after: 120, label: "Almost done…" },
];

export function ContentUploader({ onResult, onError, label, persona }: Props) {
  const [loading, setLoading] = useState(false);
  const [loadingLabel, setLoadingLabel] = useState("Sending…");
  const [ytUrl, setYtUrl] = useState("");
  const [txt, setTxt] = useState("");
  const [dragging, setDragging] = useState(false);
  const timerRef = useRef<ReturnType<typeof setTimeout>[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

  function clearTimers() {
    timerRef.current.forEach(clearTimeout);
    timerRef.current = [];
  }

  function cancel() {
    abortRef.current?.abort();
    abortRef.current = null;
    clearTimers();
    setLoading(false);
  }

  useEffect(() => () => {
    abortRef.current?.abort();
    abortRef.current = null;
    timerRef.current.forEach(clearTimeout);
  }, []);

  async function submit(form: FormData) {
    if (persona && persona !== "default") {
      form.append("persona", persona);
    }
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setLoadingLabel(STAGES[0].label);
    clearTimers();
    STAGES.slice(1).forEach(({ after, label: lbl }) => {
      timerRef.current.push(setTimeout(() => {
        if (abortRef.current === controller) setLoadingLabel(lbl);
      }, after * 1000));
    });
    try {
      const res = await fetch(`${BASE}/analyze`, { method: "POST", body: form, signal: controller.signal });
      if (!res.ok) {
        const body = await res.text();
        let detail = body;
        try { detail = JSON.parse(body).detail ?? body; } catch { /* not JSON */ }
        throw new Error(res.status === 503 ? `Not enough RAM — ${detail}` : detail);
      }
      const result = await res.json();
      if (abortRef.current === controller) onResult(result);
    } catch (e) {
      if (abortRef.current !== controller) return;
      if (e instanceof DOMException && e.name === "AbortError") return;
      onError(e instanceof Error ? e.message : "Cannot reach the analysis server. Make sure the backend is running.");
    } finally {
      if (abortRef.current === controller) {
        clearTimers();
        setLoading(false);
        abortRef.current = null;
      }
    }
  }

  function handleFile(file: File) {
    const f = new FormData(); f.append("file", file); submit(f);
  }

  return (
    <div className="w-full max-w-xl">
      {label && <p className="text-sm font-medium text-muted-foreground mb-2">{label}</p>}
      <Tabs defaultValue="file">
        <TabsList className="w-full">
          <TabsTrigger value="file" className="flex-1"><Upload className="w-4 h-4 mr-1" />File</TabsTrigger>
          <TabsTrigger value="youtube" className="flex-1"><Link className="w-4 h-4 mr-1" />Video URL</TabsTrigger>
          <TabsTrigger value="text" className="flex-1"><FileText className="w-4 h-4 mr-1" />Text</TabsTrigger>
        </TabsList>

        <TabsContent value="file">
          <label
            onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f) handleFile(f); }}
            className={`block border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-colors ${dragging ? "border-primary bg-primary/5" : "border-border hover:border-primary/50"}`}
          >
            <Upload className="w-8 h-8 mx-auto mb-3 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Drop image, video, or PDF<br />
              <span className="text-xs">JPG PNG MP4 MOV PDF supported</span>
            </p>
            <input type="file" className="sr-only"
              accept=".jpg,.jpeg,.png,.gif,.webp,.mp4,.mov,.avi,.pdf"
              onChange={(e) => { const f = e.target.files?.[0]; if (f) handleFile(f); }} />
          </label>
        </TabsContent>

        <TabsContent value="youtube">
          <div className="flex gap-2 mt-2">
            <input type="url" value={ytUrl} onChange={(e) => setYtUrl(e.target.value)}
              placeholder="YouTube, TikTok, Instagram, Twitter/X, Vimeo..."
              className="flex-1 px-3 py-2 text-sm border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary" />
            <Button disabled={!ytUrl || loading} onClick={() => { const f = new FormData(); f.append("youtube_url", ytUrl); submit(f); }}>
              {loading ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />{loadingLabel}</> : "Analyze"}
            </Button>
          </div>
        </TabsContent>

        <TabsContent value="text">
          <textarea value={txt} onChange={(e) => setTxt(e.target.value)}
            placeholder="Paste ad copy, script, book chapter, or any text..."
            rows={5}
            className="w-full px-3 py-2 text-sm border rounded-lg bg-background resize-none focus:outline-none focus:ring-2 focus:ring-primary mt-2" />
          <Button disabled={!txt.trim() || loading} className="w-full mt-2"
            onClick={() => { const f = new FormData(); f.append("text_content", txt); submit(f); }}>
            {loading ? <><Loader2 className="w-4 h-4 animate-spin mr-2" />{loadingLabel}</> : "Analyze Brain Response"}
          </Button>
        </TabsContent>
      </Tabs>

      {loading && (
        <div className="mt-3 flex items-center justify-between px-3 py-2 rounded-lg border border-border bg-muted/40">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
            <span>{loadingLabel}</span>
          </div>
          <button
            onClick={cancel}
            className="flex items-center gap-1 text-xs text-muted-foreground hover:text-destructive transition-colors"
          >
            <X className="w-3.5 h-3.5" />
            Cancel
          </button>
        </div>
      )}
    </div>
  );
}
