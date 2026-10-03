"use client";
import { useEffect, useState, useCallback, useRef } from "react";
import { Cpu, Mic, X } from "lucide-react";

interface StatusData {
  loaded: boolean;
  available?: boolean;
  idle_timeout_seconds: number;
  idle_for_seconds: number | null;
  available_memory_gb?: number;
}

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface ModelBadgeProps {
  label: string;
  loadedLabel: string;
  unloadedLabel: string;
  icon: React.ReactNode;
  statusEndpoint: string;
  unloadEndpoint: string;
}

function ModelBadge({ loadedLabel, unloadedLabel, icon, statusEndpoint, unloadEndpoint }: ModelBadgeProps) {
  const [status, setStatus] = useState<StatusData | null>(null);
  const [unloading, setUnloading] = useState(false);
  const unloadingRef = useRef(false);

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${BASE}${statusEndpoint}`);
      if (res.ok) {
        return await res.json() as StatusData;
      }
    } catch {
      // backend not running
    }
    return null;
  }, [statusEndpoint]);

  useEffect(() => {
    let active = true;
    const refresh = () => {
      fetchStatus().then((nextStatus) => {
        if (active) setStatus(nextStatus);
      });
    };
    refresh();
    const id = setInterval(refresh, 30_000);
    return () => { active = false; clearInterval(id); };
  }, [fetchStatus]);

  async function handleUnload() {
    if (unloadingRef.current) return;
    unloadingRef.current = true;
    setUnloading(true);
    try {
      const res = await fetch(`${BASE}${unloadEndpoint}`, { method: "POST" });
      if (res.ok) {
        setStatus(await fetchStatus());
      } else {
        console.error("Unload failed:", res.status);
      }
    } catch {
      // backend not reachable
    } finally {
      unloadingRef.current = false;
      setUnloading(false);
    }
  }

  // Hide when backend is down or model explicitly not installed
  if (!status || status.available === false) return null;

  return (
    <div
      className={`flex items-center gap-2 px-3 py-2 rounded-lg border text-xs shadow-sm backdrop-blur-sm ${
        status.loaded
          ? "bg-emerald-50 border-emerald-200 text-emerald-700 dark:bg-emerald-950/30 dark:border-emerald-800 dark:text-emerald-400"
          : "bg-zinc-50 border-zinc-200 text-zinc-500 dark:bg-zinc-900/50 dark:border-zinc-700 dark:text-zinc-500"
      }`}
    >
      {icon}
      <span className="font-medium">{status.loaded ? loadedLabel : unloadedLabel}</span>
      {status.loaded && status.idle_for_seconds !== null && (
        <span className="text-xs opacity-70">· idle {Math.round(status.idle_for_seconds)}s</span>
      )}
      {status.loaded && (
        <button
          onClick={handleUnload}
          disabled={unloading}
          aria-label={`Unload ${loadedLabel}`}
          className="ml-1 hover:opacity-70 transition-opacity disabled:opacity-40"
        >
          <X className="w-3 h-3" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}

export function ModelStatusBar() {
  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 items-end">
      <ModelBadge
        label="vlm"
        loadedLabel="VLM loaded"
        unloadedLabel="VLM unloaded"
        icon={<Cpu className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />}
        statusEndpoint="/model/status"
        unloadEndpoint="/model/unload"
      />
      <ModelBadge
        label="whisper"
        loadedLabel="Whisper loaded"
        unloadedLabel="Whisper unloaded"
        icon={<Mic className="w-3.5 h-3.5 shrink-0" aria-hidden="true" />}
        statusEndpoint="/whisper/status"
        unloadEndpoint="/whisper/unload"
      />
    </div>
  );
}
