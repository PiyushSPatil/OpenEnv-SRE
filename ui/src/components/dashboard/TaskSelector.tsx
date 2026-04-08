import { TASK_OPTIONS, type Difficulty } from '@/lib/simulator';
import { Settings2 } from 'lucide-react';

interface TaskSelectorProps {
  value: Difficulty;
  onChange: (d: Difficulty) => void;
  disabled: boolean;
}

export function TaskSelector({ value, onChange, disabled }: TaskSelectorProps) {
  return (
    <div className="glass-card">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-glass-border">
        <Settings2 className="h-4 w-4 text-primary" />
        <span className="text-sm font-medium text-foreground">Scenario</span>
      </div>
      <div className="p-4">
        <select
          value={value}
          onChange={(e) => onChange(e.target.value as Difficulty)}
          disabled={disabled}
          className="w-full px-3 py-2.5 text-sm font-mono rounded-xl bg-secondary border border-glass-border text-foreground focus:outline-none focus:ring-1 focus:ring-primary disabled:opacity-50"
        >
          {TASK_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      </div>
    </div>
  );
}
