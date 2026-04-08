// Mock API layer for the AI SRE Simulator

export type LogLevel = 'ERROR' | 'WARN' | 'INFO';
export type SystemStatus = 'healthy' | 'degraded' | 'critical';
export type Difficulty = 'easy' | 'medium' | 'hard';
export type ActionType = 'restart_service' | 'fix_db' | 'clear_cache' | 'scale_service' | 'noop';

export interface LogEntry {
  id: string;
  level: LogLevel;
  message: string;
  timestamp: string;
}

export interface Alert {
  id: string;
  severity: 'critical' | 'warning';
  message: string;
  active: boolean;
}

export interface Metrics {
  cpu: number;
  latency: number;
  memory: number;
  requestsPerSec: number;
}

export interface SimState {
  status: SystemStatus;
  metrics: Metrics;
  logs: LogEntry[];
  alerts: Alert[];
  reward: number;
  totalScore: number;
  stepCount: number;
  maxSteps: number;
  done: boolean;
  aiThinking: boolean;
  actionHistory: { action: string; step: number; reward: number }[];
}

const LOG_TEMPLATES: { level: LogLevel; message: string }[] = [
  { level: 'ERROR', message: 'DB connection timeout after 30s' },
  { level: 'ERROR', message: 'Service crash detected in pod-3' },
  { level: 'ERROR', message: 'Out of memory: killed process 1842' },
  { level: 'WARN', message: 'High latency detected: p99 > 500ms' },
  { level: 'WARN', message: 'Connection pool exhausted (95%)' },
  { level: 'WARN', message: 'Disk usage at 87%' },
  { level: 'INFO', message: 'Retrying request to upstream (attempt 3)' },
  { level: 'INFO', message: 'Health check passed for pod-1' },
  { level: 'INFO', message: 'Cache invalidation completed' },
  { level: 'INFO', message: 'Auto-scaling triggered: 3 → 5 replicas' },
];

const RECOVERY_LOGS: { level: LogLevel; message: string }[] = [
  { level: 'INFO', message: 'Service restarted successfully' },
  { level: 'INFO', message: 'DB connection re-established' },
  { level: 'INFO', message: 'Cache cleared: 2.4GB freed' },
  { level: 'INFO', message: 'Horizontal scaling complete' },
  { level: 'INFO', message: 'Latency normalized: p99 < 100ms' },
];

const TASK_CONFIGS: Record<Difficulty, { name: string; maxSteps: number; initialStatus: SystemStatus }> = {
  easy: { name: 'Fix latency issue', maxSteps: 10, initialStatus: 'degraded' },
  medium: { name: 'Resolve DB failure', maxSteps: 15, initialStatus: 'critical' },
  hard: { name: 'Handle full system outage', maxSteps: 20, initialStatus: 'critical' },
};

let uid = 0;
const genId = () => `log-${++uid}`;
const now = () => new Date().toISOString().split('T')[1].split('.')[0];

function randomMetrics(status: SystemStatus): Metrics {
  const base = status === 'healthy' ? 0 : status === 'degraded' ? 1 : 2;
  return {
    cpu: Math.min(99, 20 + base * 25 + Math.random() * 20),
    latency: 50 + base * 200 + Math.random() * 100,
    memory: 30 + base * 20 + Math.random() * 15,
    requestsPerSec: Math.max(10, 500 - base * 180 + Math.random() * 50),
  };
}

function generateAlerts(status: SystemStatus): Alert[] {
  if (status === 'healthy') return [];
  const alerts: Alert[] = [
    { id: 'a1', severity: 'warning', message: 'High latency on /api/users', active: true },
  ];
  if (status === 'critical') {
    alerts.push(
      { id: 'a2', severity: 'critical', message: 'Database connection failure', active: true },
      { id: 'a3', severity: 'critical', message: 'Service pod-3 unresponsive', active: true },
    );
  }
  return alerts;
}

export function createInitialState(difficulty: Difficulty): SimState {
  const config = TASK_CONFIGS[difficulty];
  const status = config.initialStatus;
  const errorLogs = LOG_TEMPLATES.filter(l => l.level === 'ERROR' || (status === 'critical' && l.level === 'WARN'));
  const initialLogs: LogEntry[] = errorLogs.slice(0, 4).map(l => ({
    id: genId(),
    level: l.level,
    message: l.message,
    timestamp: now(),
  }));

  return {
    status,
    metrics: randomMetrics(status),
    logs: initialLogs,
    alerts: generateAlerts(status),
    reward: 0,
    totalScore: 0,
    stepCount: 0,
    maxSteps: config.maxSteps,
    done: false,
    aiThinking: false,
    actionHistory: [],
  };
}

const ACTION_EFFECTS: Record<ActionType, (state: SimState) => { reward: number; newStatus: SystemStatus; log: LogEntry }> = {
  restart_service: (state) => {
    const improving = state.status === 'critical' ? 'degraded' : 'healthy';
    return {
      reward: state.status !== 'healthy' ? 0.3 : -0.1,
      newStatus: improving as SystemStatus,
      log: { id: genId(), level: 'INFO', message: 'Service restarted successfully', timestamp: now() },
    };
  },
  fix_db: (state) => {
    const hasDbAlert = state.alerts.some(a => a.message.includes('Database'));
    return {
      reward: hasDbAlert ? 0.5 : -0.1,
      newStatus: hasDbAlert ? (state.status === 'critical' ? 'degraded' : 'healthy') : state.status,
      log: { id: genId(), level: hasDbAlert ? 'INFO' : 'WARN', message: hasDbAlert ? 'DB connection re-established' : 'No DB issue found, action wasted', timestamp: now() },
    };
  },
  clear_cache: (state) => ({
    reward: state.metrics.memory > 60 ? 0.2 : 0.0,
    newStatus: state.status,
    log: { id: genId(), level: 'INFO', message: 'Cache cleared: 2.4GB freed', timestamp: now() },
  }),
  scale_service: (state) => ({
    reward: state.metrics.cpu > 70 ? 0.3 : 0.0,
    newStatus: state.metrics.cpu > 70 ? (state.status === 'critical' ? 'degraded' : state.status) : state.status,
    log: { id: genId(), level: 'INFO', message: 'Horizontal scaling complete: 3 → 5 replicas', timestamp: now() },
  }),
  noop: () => ({
    reward: -0.05,
    newStatus: 'degraded' as SystemStatus,
    log: { id: genId(), level: 'WARN', message: 'No action taken — system unchanged', timestamp: now() },
  }),
};

export function simulateStep(state: SimState, action: ActionType): SimState {
  const effect = ACTION_EFFECTS[action](state);
  const newStep = state.stepCount + 1;
  const done = newStep >= state.maxSteps || effect.newStatus === 'healthy';

  // Add some random ambient logs
  const ambientLog = LOG_TEMPLATES[Math.floor(Math.random() * LOG_TEMPLATES.length)];
  const newLogs = [
    ...state.logs,
    { id: genId(), level: ambientLog.level, message: ambientLog.message, timestamp: now() },
    effect.log,
  ].slice(-50); // Keep last 50 logs

  if (done && effect.newStatus === 'healthy') {
    newLogs.push(...RECOVERY_LOGS.slice(0, 2).map(l => ({ ...l, id: genId(), timestamp: now() })));
  }

  return {
    status: effect.newStatus,
    metrics: randomMetrics(effect.newStatus),
    logs: newLogs,
    alerts: generateAlerts(effect.newStatus),
    reward: effect.reward,
    totalScore: +(state.totalScore + effect.reward).toFixed(2),
    stepCount: newStep,
    maxSteps: state.maxSteps,
    done,
    aiThinking: false,
    actionHistory: [...state.actionHistory, { action, step: newStep, reward: effect.reward }],
  };
}

// AI agent mock — picks a reasonable action
export function aiPickAction(state: SimState): ActionType {
  if (state.alerts.some(a => a.message.includes('Database'))) return 'fix_db';
  if (state.metrics.cpu > 70) return 'scale_service';
  if (state.metrics.memory > 60) return 'clear_cache';
  if (state.status !== 'healthy') return 'restart_service';
  return 'noop';
}

export const TASK_OPTIONS: { value: Difficulty; label: string }[] = [
  { value: 'easy', label: '🟢 Easy: Fix latency issue' },
  { value: 'medium', label: '🟡 Medium: Resolve DB failure' },
  { value: 'hard', label: '🔴 Hard: Handle full system outage' },
];

export const ACTION_LABELS: Record<ActionType, string> = {
  restart_service: 'Restart Service',
  fix_db: 'Fix DB Connection',
  clear_cache: 'Clear Cache',
  scale_service: 'Scale Service',
  noop: 'Noop',
};
