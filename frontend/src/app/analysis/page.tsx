"use client";
import { useEffect, useMemo, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { BrainRadarChart } from "@/components/BrainRadarChart";
import { RegionCard } from "@/components/RegionCard";
import { RecommendationPanel } from "@/components/RecommendationPanel";
import { SaveProjectButton } from "@/components/SaveProjectButton";
import { ShareButton } from "@/components/ShareButton";
import { Headline } from "@/components/Headline";
import { Button } from "@/components/ui/button";
import { ArrowLeft, BarChart2, FolderOpen } from "lucide-react";
import type { AnalysisResult, BrainScores } from "@/types/analysis";

function subscribeToStorage(callback: () => void) {
  window.addEventListener("storage", callback);
  return () => window.removeEventListener("storage", callback);
}

function readStoredResult() {
  try { return sessionStorage.getItem("np_result"); }
  catch { return null; }
}

const SCORE_KEYS: (keyof BrainScores)[] = [
  "visual_cortex", "face_social", "amygdala", "hippocampus",
  "language_areas", "reward_circuit", "prefrontal", "motor_action",
];

function parseStoredResult(raw: string | null | undefined): AnalysisResult | null {
  if (!raw) return null;
  try {
    const value = JSON.parse(raw) as AnalysisResult;
    if (!value || typeof value !== "object" || !value.scores ||
      Object.keys(value.scores).length !== SCORE_KEYS.length ||
      !SCORE_KEYS.every((key) => typeof value.scores[key] === "number" && Number.isFinite(value.scores[key])) ||
      !["image", "video", "youtube", "pdf", "text"].includes(value.type) ||
      (value.headline !== undefined && typeof value.headline !== "string") ||
      !Array.isArray(value.recommendations) ||
      !value.recommendations.every((r) => r && SCORE_KEYS.includes(r.region_key) &&
        ["high", "medium", "ok"].includes(r.priority) &&
        typeof r.region_name === "string" && typeof r.score === "number" &&
        typeof r.message === "string" && typeof r.details === "string" &&
        Array.isArray(r.steps) && r.steps.every((step) => typeof step === "string"))) return null;
    return value;
  } catch { return null; }
}

export default function AnalysisPage() {
  const router = useRouter();
  const raw = useSyncExternalStore(subscribeToStorage, readStoredResult, () => undefined);
  const result = useMemo(() => parseStoredResult(raw), [raw]);

  useEffect(() => {
    if (raw === undefined || result) return;
    try { sessionStorage.removeItem("np_result"); } catch { /* storage unavailable */ }
    router.replace("/");
  }, [raw, result, router]);

  if (!result) return null;

  const keys = Object.keys(result.scores) as (keyof BrainScores)[];
  const avg = Math.round(Object.values(result.scores).reduce((a, b) => a + b, 0) / keys.length);

  return (
    <main className="min-h-screen px-4 py-10 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-8 flex-wrap">
        <Button variant="ghost" size="sm" onClick={() => router.push("/")}>
          <ArrowLeft className="w-4 h-4 mr-1" /> New
        </Button>
        <Button variant="outline" size="sm" onClick={() => router.push("/compare")}>
          <BarChart2 className="w-4 h-4 mr-1" /> Compare
        </Button>
        <Button variant="outline" size="sm" onClick={() => router.push("/projects")}>
          <FolderOpen className="w-4 h-4 mr-1" /> Projects
        </Button>
        <div className="ml-auto flex items-center gap-2 flex-wrap">
          <ShareButton result={result} />
          <SaveProjectButton result={result} />
        </div>
      </div>

      <Headline text={result.headline} />

      <div className="grid md:grid-cols-2 gap-8 mb-8">
        <div>
          <h2 className="text-2xl font-bold mb-1">Brain Activation</h2>
          <p className="text-muted-foreground text-sm mb-4">
            Overall: <span className="font-semibold text-foreground">{avg}/100</span>
            <span className="ml-2 capitalize text-xs">({result.type})</span>
          </p>
          <BrainRadarChart scores={result.scores} />
        </div>
        <div className="space-y-2">
          <h3 className="font-semibold mb-3">Region Breakdown</h3>
          {keys.map((k) => <RegionCard key={k} regionKey={k} score={result.scores[k]} />)}
        </div>
      </div>

      <RecommendationPanel recommendations={result.recommendations} />
    </main>
  );
}
