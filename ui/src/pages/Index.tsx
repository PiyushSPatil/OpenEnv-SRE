import { useState, useCallback, useEffect, useRef } from "react";
import confetti from "canvas-confetti";

import { DashboardHeader } from "@/components/dashboard/DashboardHeader";
import { LogsPanel } from "@/components/dashboard/LogsPanel";
import { MetricsPanel } from "@/components/dashboard/MetricsPanel";
import { AlertsPanel } from "@/components/dashboard/AlertsPanel";
import { ActionsPanel } from "@/components/dashboard/ActionsPanel";
import { RewardPanel } from "@/components/dashboard/RewardPanel";
import { TaskSelector } from "@/components/dashboard/TaskSelector";
import { ActionTimeline } from "@/components/dashboard/ActionTimeline";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:7860";

// ---------------- TASK MAPPING ----------------
const mapTask = (difficulty: string) => {
  if (difficulty === "easy") return "easy_cache";
  if (difficulty === "medium") return "medium_db";
  if (difficulty === "hard") return "hard_outage";
  return "easy_cache";
};

// ---------------- TRANSFORM BACKEND → UI ----------------
const transformObservation = (obs: any) => {
  // ---- FIX LOGS ----
  const parsedLogs = (obs.logs || []).map((log: string, i: number) => {
    const match = log.match(/\[(.*?)\]\s*(.*)/);

    return {
      id: i,
      timestamp: new Date().toLocaleTimeString(),
      level: match ? match[1] : "INFO",
      message: match ? match[2] : log,
    };
  });

  // ---- FIX ALERTS ----
  const parsedAlerts = (obs.alerts || []).map((alert: string, i: number) => ({
    id: i,
    severity: alert.toLowerCase().includes("critical") ? "critical" : "warning",
    message: alert,
  }));

  return {
    logs: parsedLogs,
    alerts: parsedAlerts,

    // ---- FIX METRICS ----
    metrics: {
      cpu: obs.metrics?.cpu ?? 0,
      latency: obs.metrics?.latency ?? 0,
      memory: 70,
      requestsPerSec: 100, // IMPORTANT FIX
    },

    // ---- FIX STATUS ----
    status: obs.system_status || "degraded", // MUST be string

    stepCount: obs.step_count ?? 0,
    maxSteps: obs.max_steps ?? 6,

    done: false,
  };
};

export default function Index() {
  const [difficulty, setDifficulty] = useState("medium");

  const [state, setState] = useState<any>(null);
  const [reward, setReward] = useState(0);
  const [totalScore, setTotalScore] = useState(0);
  const [done, setDone] = useState(false);
  const [aiThinking, setAiThinking] = useState(false);
  const [history, setHistory] = useState<any[]>([]);

  // ---------------- RESET ----------------
  const handleReset = useCallback(async (d: string) => {
    try {
      const task_id = mapTask(d);

      const res = await fetch(`${API_BASE}/reset`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task_id }),
      });

      const data = await res.json();

      const transformed = transformObservation(data.observation);

      setState(transformed);
      setReward(0);
      setTotalScore(0);
      setDone(false);
      setHistory([]);
      setDifficulty(d);
    } catch (err) {
      console.error("RESET ERROR:", err);
    }
  }, []);

  // ---------------- ACTION ----------------
  const handleAction = useCallback(
    async (action_type: string) => {
      if (done) return;

      try {
        const res = await fetch(`${API_BASE}/step`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ action_type }),
        });

        const data = await res.json();

        const transformed = transformObservation(data.observation);

        setState(transformed);
        setReward(data.reward?.value || 0);
        setTotalScore((prev) => prev + (data.reward?.value || 0));
        setDone(data.done);

        setHistory((prev) => [
          ...prev,
          {
            action: action_type,
            reward: data.reward?.value || 0,
          },
        ]);
      } catch (err) {
        console.error("STEP ERROR:", err);
      }
    },
    [done],
  );

  // ---------------- AI RUN ----------------
  const handleAiRun = useCallback(async () => {
    setAiThinking(true);

    for (let i = 0; i < 6; i++) {
      if (done) break;
      await handleAction("noop"); // later replace with smart AI
    }

    setAiThinking(false);
  }, [handleAction, done]);

  // ---------------- NEXT STEP ----------------
  const handleNextStep = useCallback(() => {
    handleAction("noop");
  }, [handleAction]);

  // ---------------- RECOVERY EFFECT ----------------
  const prevStatusRef = useRef<string | null>(null);
  const [recovered, setRecovered] = useState(false);

  useEffect(() => {
    if (!state) return;

    if (prevStatusRef.current !== "healthy" && state.raw_status === "healthy") {
      setRecovered(true);
      confetti({ particleCount: 120, spread: 80 });
      setTimeout(() => setRecovered(false), 3000);
    }

    prevStatusRef.current = state.raw_status;
  }, [state]);

  // ---------------- INITIAL LOAD ----------------
  useEffect(() => {
    handleReset("medium");
  }, []);

  if (!state) return <div className="text-white p-10">Loading...</div>;

  return (
    <div className="h-screen flex flex-col p-3 md:p-4 max-w-[1440px] mx-auto">
      <DashboardHeader status={state.status} />

      {/* TOP */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 flex-1">
        <div className="lg:col-span-5">
          <LogsPanel logs={state.logs} />
        </div>
        <div className="lg:col-span-3">
          <MetricsPanel metrics={state.metrics} />
        </div>
        <div className="lg:col-span-4">
          <AlertsPanel alerts={state.alerts} />
        </div>
      </div>

      {/* BOTTOM */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-3 mt-3">
        <div className="lg:col-span-2">
          <TaskSelector
            value={difficulty}
            onChange={handleReset}
            disabled={state.stepCount > 0 && !done}
          />
        </div>

        <div className="lg:col-span-4">
          <ActionsPanel
            onAction={handleAction}
            onAiRun={handleAiRun}
            onNextStep={handleNextStep}
            disabled={done || aiThinking}
            aiThinking={aiThinking}
          />
        </div>

        <div className="lg:col-span-3">
          <RewardPanel
            reward={reward}
            totalScore={totalScore}
            stepCount={state.stepCount}
            maxSteps={state.maxSteps}
            done={done}
          />
        </div>

        <div className="lg:col-span-3">
          <ActionTimeline history={history} />
        </div>
      </div>
    </div>
  );
}
