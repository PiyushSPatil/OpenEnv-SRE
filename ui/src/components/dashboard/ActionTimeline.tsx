import { motion } from 'framer-motion';
import { Clock } from 'lucide-react';
import { ACTION_LABELS, type ActionType } from '@/lib/simulator';

interface ActionTimelineProps {
  history: { action: string; step: number; reward: number }[];
}

export function ActionTimeline({ history }: ActionTimelineProps) {
  return (
    <div className="glass-card">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-glass-border">
        <Clock className="h-4 w-4 text-accent" />
        <span className="text-sm font-medium text-foreground">Action Timeline</span>
      </div>
      <div className="p-3 max-h-[160px] overflow-y-auto scrollbar-thin">
        {history.length === 0 ? (
          <p className="text-xs text-muted-foreground text-center py-4">No actions taken yet</p>
        ) : (
          <div className="space-y-2">
            {history.map((entry, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                className="flex items-center gap-3 text-xs font-mono"
              >
                <span className="text-muted-foreground w-6 text-right">#{entry.step}</span>
                <div className="h-1.5 w-1.5 rounded-full bg-primary shrink-0" />
                <span className="text-secondary-foreground flex-1">
                  {ACTION_LABELS[entry.action as ActionType] ?? entry.action}
                </span>
                <span className={`font-semibold ${entry.reward > 0 ? 'text-primary' : entry.reward < 0 ? 'text-destructive' : 'text-muted-foreground'}`}>
                  {entry.reward > 0 ? '+' : ''}{entry.reward.toFixed(2)}
                </span>
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
