import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Terminal } from 'lucide-react';
import type { LogEntry } from '@/lib/simulator';

const LEVEL_CLASS: Record<string, string> = {
  ERROR: 'log-error',
  WARN: 'log-warn',
  INFO: 'log-info',
};

export function LogsPanel({ logs }: { logs: LogEntry[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs.length]);

  return (
    <div className="glass-card flex flex-col h-full">
      <div className="flex items-center gap-2 px-4 py-3 border-b border-glass-border">
        <Terminal className="h-4 w-4 text-primary" />
        <span className="text-sm font-medium text-foreground">System Logs</span>
        <span className="ml-auto text-xs text-muted-foreground font-mono">{logs.length} entries</span>
      </div>
      <div className="flex-1 overflow-y-auto p-3 scrollbar-thin min-h-0">
        <AnimatePresence initial={false}>
          {logs.map((log) => (
            <motion.div
              key={log.id}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.2 }}
              className="flex gap-2 py-1 font-mono text-xs leading-relaxed"
            >
              <span className="text-muted-foreground shrink-0">{log.timestamp}</span>
              <span className={`font-semibold shrink-0 w-12 ${LEVEL_CLASS[log.level]}`}>[{log.level}]</span>
              <span className="text-secondary-foreground">{log.message}</span>
            </motion.div>
          ))}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
