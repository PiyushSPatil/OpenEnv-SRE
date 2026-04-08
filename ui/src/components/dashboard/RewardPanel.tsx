import { motion } from 'framer-motion';
import { Trophy, Hash, TrendingUp } from 'lucide-react';

interface RewardPanelProps {
  reward: number;
  totalScore: number;
  stepCount: number;
  maxSteps: number;
  done: boolean;
}

export function RewardPanel({ reward, totalScore, stepCount, maxSteps, done }: RewardPanelProps) {
  const progress = (stepCount / maxSteps) * 100;

  return (
    <div className="glass-card">
      <div className="flex items-center gap-2 px-4 py-2 border-b border-glass-border">
        <Trophy className="h-4 w-4 text-warning" />
        <span className="text-sm font-medium text-foreground">Progress</span>
      </div>
      <div className="p-3 space-y-3">
        <div className="grid grid-cols-3 gap-3">
          <div className="text-center p-2 rounded-xl bg-secondary/50 border border-glass-border">
            <TrendingUp className="h-4 w-4 mx-auto mb-1 text-primary" />
            <motion.div
              key={reward}
              initial={{ scale: 1.3 }}
              animate={{ scale: 1 }}
              className={`text-lg font-bold font-mono ${reward > 0 ? 'text-primary' : reward < 0 ? 'text-destructive' : 'text-muted-foreground'}`}
            >
              {reward > 0 ? '+' : ''}{reward.toFixed(2)}
            </motion.div>
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Reward</span>
          </div>
          <div className="text-center p-2 rounded-xl bg-secondary/50 border border-glass-border">
            <Trophy className="h-4 w-4 mx-auto mb-1 text-warning" />
            <div className="text-lg font-bold font-mono text-foreground">{totalScore.toFixed(2)}</div>
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Score</span>
          </div>
          <div className="text-center p-2 rounded-xl bg-secondary/50 border border-glass-border">
            <Hash className="h-4 w-4 mx-auto mb-1 text-accent" />
            <div className="text-lg font-bold font-mono text-foreground">{stepCount}/{maxSteps}</div>
            <span className="text-[10px] text-muted-foreground uppercase tracking-wider">Steps</span>
          </div>
        </div>

        {/* Inline progress bar */}
        <div>
          <div className="flex justify-between text-[10px] text-muted-foreground mb-1">
            <span>{done ? '✓ Complete' : 'Progress'}</span>
            <span>{progress.toFixed(0)}%</span>
          </div>
          <div className="metric-bar">
            <motion.div
              className={`metric-bar-fill ${done ? 'bg-primary' : 'bg-accent'}`}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}