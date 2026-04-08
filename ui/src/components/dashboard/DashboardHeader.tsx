import { motion } from 'framer-motion';
import { Activity } from 'lucide-react';

// Remove strict typing dependency to avoid crashes
type SystemStatus = 'healthy' | 'degraded' | 'critical';

const STATUS_CONFIG: Record<SystemStatus, { label: string; class: string; glow: string }> = {
  healthy: { label: 'Healthy', class: 'status-healthy', glow: 'glow-green' },
  degraded: { label: 'Degraded', class: 'status-degraded', glow: 'glow-orange' },
  critical: { label: 'Critical', class: 'status-critical', glow: 'glow-red' },
};

export function DashboardHeader({ status }: { status: any }) {

  // ✅ SAFE FALLBACK (VERY IMPORTANT)
  const safeStatus: SystemStatus =
    status === 'healthy' || status === 'critical'
      ? status
      : 'degraded';

  const cfg = STATUS_CONFIG[safeStatus];

  return (
    <header className="flex items-center justify-between px-6 py-4 glass-card mb-4">
      
      <div className="flex items-center gap-3">
        <Activity className="h-6 w-6 text-primary" />
        <div>
          <h1 className="text-xl font-semibold font-heading text-foreground tracking-tight">
            AI SRE Simulator
          </h1>
          <p className="text-xs text-muted-foreground">
            Autonomous DevOps Incident Response Environment
          </p>
        </div>
      </div>

      <motion.div
        key={safeStatus}
        initial={{ scale: 0.8, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className={`flex items-center gap-2 px-4 py-2 rounded-full border border-glass-border ${cfg.glow}`}
      >
        <span
          className={`h-2.5 w-2.5 rounded-full bg-current ${cfg.class} animate-pulse-glow`}
        />
        <span className={`text-sm font-medium font-mono ${cfg.class}`}>
          {cfg.label}
        </span>
      </motion.div>

    </header>
  );
}