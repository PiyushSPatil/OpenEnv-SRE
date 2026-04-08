import { motion } from 'framer-motion';
import { Bot, ChevronRight, RotateCcw, Database, Trash2, ArrowUpCircle, Circle } from 'lucide-react';
import { type ActionType, ACTION_LABELS } from '@/lib/simulator';

const ACTION_ICONS: Record<ActionType, React.ReactNode> = {
  restart_service: <RotateCcw className="h-3.5 w-3.5" />,
  fix_db: <Database className="h-3.5 w-3.5" />,
  clear_cache: <Trash2 className="h-3.5 w-3.5" />,
  scale_service: <ArrowUpCircle className="h-3.5 w-3.5" />,
  noop: <Circle className="h-3.5 w-3.5" />,
};

interface ActionsPanelProps {
  onAction: (action: ActionType) => void;
  onAiRun: () => void;
  onNextStep: () => void;
  disabled: boolean;
  aiThinking: boolean;
}

export function ActionsPanel({ onAction, onAiRun, onNextStep, disabled, aiThinking }: ActionsPanelProps) {
  const actions: ActionType[] = ['restart_service', 'fix_db', 'clear_cache', 'scale_service', 'noop'];

  return (
    <div className="glass-card">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-glass-border">
        <ChevronRight className="h-4 w-4 text-primary" />
        <span className="text-sm font-medium text-foreground">Actions</span>
      </div>
      <div className="p-4 space-y-3">
        <div className="grid grid-cols-2 gap-2">
          {actions.map((action) => (
            <button
              key={action}
              onClick={() => onAction(action)}
              disabled={disabled}
              className="flex items-center gap-2 px-3 py-2.5 text-xs font-medium rounded-xl border border-glass-border bg-secondary/50 text-secondary-foreground hover:bg-secondary hover:border-primary/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {ACTION_ICONS[action]}
              {ACTION_LABELS[action]}
            </button>
          ))}
        </div>
        <div className="flex gap-2 pt-2 border-t border-glass-border">
          <button
            onClick={onAiRun}
            disabled={disabled}
            className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 text-xs font-semibold rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {aiThinking ? (
              <motion.span
                animate={{ opacity: [1, 0.4, 1] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                className="flex items-center gap-2"
              >
                <Bot className="h-4 w-4" />
                AI Thinking...
              </motion.span>
            ) : (
              <>
                <Bot className="h-4 w-4" />
                Run AI Agent
              </>
            )}
          </button>
          <button
            onClick={onNextStep}
            disabled={disabled}
            className="px-4 py-2.5 text-xs font-medium rounded-xl border border-primary/40 text-primary hover:bg-primary/10 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Next Step
          </button>
        </div>
      </div>
    </div>
  );
}
