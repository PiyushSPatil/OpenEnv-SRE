import { useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Cpu, Clock, HardDrive, Zap } from 'lucide-react';
import { LineChart, Line, ResponsiveContainer, YAxis } from 'recharts';
import type { Metrics } from '@/lib/simulator';

const MAX_HISTORY = 20;

interface MetricRowProps {
  icon: React.ReactNode;
  label: string;
  value: string;
  pct: number;
  color: string;
  history: number[];
  sparkColor: string;
}

function MetricRow({ icon, label, value, pct, color, history, sparkColor }: MetricRowProps) {
  const data = history.map((v, i) => ({ i, v }));

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-sm text-secondary-foreground">
          {icon}
          <span>{label}</span>
        </div>
        <span className="text-sm font-mono font-medium text-foreground">{value}</span>
      </div>
      <div className="flex items-center gap-2">
        <div className="metric-bar flex-1">
          <motion.div
            className={`metric-bar-fill ${color}`}
            initial={{ width: 0 }}
            animate={{ width: `${Math.min(pct, 100)}%` }}
            transition={{ duration: 0.7, ease: 'easeOut' }}
          />
        </div>
        {data.length > 1 && (
          <div className="w-16 h-6 shrink-0">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <YAxis domain={['dataMin', 'dataMax']} hide />
                <Line
                  type="monotone"
                  dataKey="v"
                  stroke={sparkColor}
                  strokeWidth={1.5}
                  dot={false}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}

export function MetricsPanel({ metrics }: { metrics: Metrics }) {
  const historyRef = useRef<{ cpu: number[]; latency: number[]; memory: number[]; rps: number[] }>({
    cpu: [], latency: [], memory: [], rps: [],
  });

  useEffect(() => {
    const h = historyRef.current;
    h.cpu = [...h.cpu, metrics.cpu].slice(-MAX_HISTORY);
    h.latency = [...h.latency, metrics.latency].slice(-MAX_HISTORY);
    h.memory = [...h.memory, metrics.memory].slice(-MAX_HISTORY);
    h.rps = [...h.rps, metrics.requestsPerSec].slice(-MAX_HISTORY);
  }, [metrics]);

  const h = historyRef.current;

  return (
    <div className="glass-card h-full">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-glass-border">
        <Cpu className="h-4 w-4 text-primary" />
        <span className="text-sm font-medium text-foreground">System Metrics</span>
      </div>
      <div className="p-4 space-y-5">
        <MetricRow
          icon={<Cpu className="h-3.5 w-3.5" />}
          label="CPU Usage"
          value={`${metrics.cpu.toFixed(1)}%`}
          pct={metrics.cpu}
          color={metrics.cpu > 80 ? 'bg-destructive' : metrics.cpu > 50 ? 'bg-warning' : 'bg-primary'}
          history={h.cpu}
          sparkColor={metrics.cpu > 80 ? '#ef4444' : metrics.cpu > 50 ? '#f59e0b' : '#00ff88'}
        />
        <MetricRow
          icon={<Clock className="h-3.5 w-3.5" />}
          label="Latency"
          value={`${metrics.latency.toFixed(0)}ms`}
          pct={metrics.latency / 10}
          color={metrics.latency > 400 ? 'bg-destructive' : metrics.latency > 200 ? 'bg-warning' : 'bg-primary'}
          history={h.latency}
          sparkColor={metrics.latency > 400 ? '#ef4444' : metrics.latency > 200 ? '#f59e0b' : '#00ff88'}
        />
        <MetricRow
          icon={<HardDrive className="h-3.5 w-3.5" />}
          label="Memory"
          value={`${metrics.memory.toFixed(1)}%`}
          pct={metrics.memory}
          color={metrics.memory > 75 ? 'bg-destructive' : metrics.memory > 50 ? 'bg-warning' : 'bg-primary'}
          history={h.memory}
          sparkColor={metrics.memory > 75 ? '#ef4444' : metrics.memory > 50 ? '#f59e0b' : '#00ff88'}
        />
        <MetricRow
          icon={<Zap className="h-3.5 w-3.5" />}
          label="Requests/sec"
          value={`${metrics.requestsPerSec.toFixed(0)}`}
          pct={metrics.requestsPerSec / 5}
          color="bg-accent"
          history={h.rps}
          sparkColor="#8b5cf6"
        />
      </div>
    </div>
  );
}
