import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle, ShieldAlert } from 'lucide-react';
import type { Alert } from '@/lib/simulator';

export function AlertsPanel({ alerts }: { alerts: Alert[] }) {
  return (
    <div className="glass-card h-full">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-glass-border">
        <AlertTriangle className="h-4 w-4 text-warning" />
        <span className="text-sm font-medium text-foreground">Active Alerts</span>
        {alerts.length > 0 && (
          <span className="ml-auto text-xs font-mono px-2 py-0.5 rounded-full bg-destructive/20 text-destructive">
            {alerts.length}
          </span>
        )}
      </div>
      <div className="p-4 space-y-3">
        <AnimatePresence mode="popLayout">
          {alerts.length === 0 ? (
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-sm text-muted-foreground text-center py-6"
            >
              No active alerts — system stable ✓
            </motion.p>
          ) : (
            alerts.map((alert) => (
              <motion.div
                key={alert.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className={`flex items-start gap-3 p-3 rounded-xl border ${
                  alert.severity === 'critical'
                    ? 'border-destructive/30 bg-destructive/10'
                    : 'border-warning/30 bg-warning/10'
                }`}
              >
                <ShieldAlert className={`h-4 w-4 mt-0.5 shrink-0 ${
                  alert.severity === 'critical' ? 'text-destructive' : 'text-warning'
                }`} />
                <div>
                  <span className={`text-xs font-mono font-semibold uppercase ${
                    alert.severity === 'critical' ? 'text-destructive' : 'text-warning'
                  }`}>
                    {alert.severity}
                  </span>
                  <p className="text-sm text-secondary-foreground mt-0.5">{alert.message}</p>
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
