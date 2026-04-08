import random
from typing import Tuple, Dict

from .models import InternalState, Observation, Reward, Action


class SRESimulator:
    """
    Realistic production-grade SRE system simulator
    """

    def __init__(self):
        self.state: InternalState = None

    # -----------------------------
    # RESET
    # -----------------------------
    def reset(self, task_id: str) -> Observation:

        if task_id == "easy_cache":
            self.state = InternalState(
                db_connected=True,
                cache_clean=False,
                services_running={"backend": True, "api": True},
                cpu_usage=60.0,
                latency=300.0,
                issue_identified=False,
                issue_fixed=False,
                step_count=0,
                max_steps=6,
                task_id=task_id,
            )

        elif task_id == "medium_db":
            self.state = InternalState(
                db_connected=False,
                cache_clean=True,
                services_running={"backend": True, "api": True},
                cpu_usage=70.0,
                latency=400.0,
                issue_identified=False,
                issue_fixed=False,
                step_count=0,
                max_steps=8,
                task_id=task_id,
            )

        elif task_id == "hard_outage":
            self.state = InternalState(
                db_connected=False,
                cache_clean=False,
                services_running={"backend": False, "api": True},
                cpu_usage=95.0,
                latency=600.0,
                issue_identified=False,
                issue_fixed=False,
                step_count=0,
                max_steps=10,
                task_id=task_id,
            )

        else:
            raise ValueError(f"Unknown task_id: {task_id}")

        return self._build_observation()

    # -----------------------------
    # STEP
    # -----------------------------
    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Dict]:

        self.state.step_count += 1
        reward_value = 0.0
        reward_reason = ""

        # -----------------------------
        # ACTIONS
        # -----------------------------
        if action.action_type == "clear_cache":
            if not self.state.cache_clean:
                self.state.cache_clean = True
                self.state.latency -= 120
                reward_value += 0.4
                reward_reason = "Cache cleared"
            else:
                reward_value -= 0.2

        elif action.action_type == "fix_db_connection":
            if not self.state.db_connected:
                self.state.db_connected = True
                self.state.latency -= 180
                reward_value += 0.5
                reward_reason = "DB fixed"
            else:
                reward_value -= 0.2

        elif action.action_type == "restart_service":
            if action.target in self.state.services_running:
                self.state.services_running[action.target] = True
                self.state.cpu_usage -= 15
                reward_value += 0.3
                reward_reason = "Service restarted"
            else:
                reward_value -= 0.3

        elif action.action_type == "scale_service":
            self.state.cpu_usage -= 20
            self.state.latency -= 40
            reward_value += 0.4
            reward_reason = "Scaled service"

        elif action.action_type == "noop":
            reward_value -= 0.1

        else:
            reward_value -= 0.5

        # -----------------------------
        # CASCADING FAILURES
        # -----------------------------
        if not self.state.db_connected:
            self.state.latency += 25

        if not self.state.cache_clean:
            self.state.latency += 15

        if not all(self.state.services_running.values()):
            self.state.cpu_usage += 8

        # -----------------------------
        # RANDOM NOISE
        # -----------------------------
        self.state.cpu_usage += random.uniform(-2, 2)
        self.state.latency += random.uniform(-5, 5)

        # -----------------------------
        # CLAMP VALUES
        # -----------------------------
        self.state.cpu_usage = max(0, min(100, self.state.cpu_usage))
        self.state.latency = max(50, self.state.latency)

        # -----------------------------
        # ISSUE DETECTION
        # -----------------------------
        if self.state.latency > 300 or not self.state.db_connected:
            self.state.issue_identified = True
            reward_value += 0.1

        # -----------------------------
        # 🔥 GRADUAL STABILIZATION BONUS
        # -----------------------------
        if self.state.latency < 300:
            reward_value += 0.1

        if self.state.cpu_usage < 80:
            reward_value += 0.1

        # -----------------------------
        # ✅ FINAL SUCCESS CONDITION (FIXED)
        # -----------------------------
        if (
            self.state.db_connected
            and all(self.state.services_running.values())
            and self.state.latency < 350
            and self.state.cpu_usage < 90
        ):
            self.state.issue_fixed = True
            reward_value += 1.0
            done = True
            reward_reason = "System recovered ✅"
        else:
            done = False

        # -----------------------------
        # STEP PENALTY
        # -----------------------------
        reward_value -= 0.05

        # -----------------------------
        # MAX STEPS
        # -----------------------------
        if self.state.step_count >= self.state.max_steps:
            done = True

        observation = self._build_observation()
        # normalize reward to 0–1
        normalized = max(0.0, min(1.0, reward_value))

        reward = Reward(value=round(normalized, 3), reason=reward_reason)

        return observation, reward, done, {}

    # -----------------------------
    # OBSERVATION
    # -----------------------------
    def _build_observation(self) -> Observation:

        logs = self._generate_logs()

        metrics = {
            "cpu": round(self.state.cpu_usage, 2),
            "latency": round(self.state.latency, 2),
        }

        alerts = []
        if self.state.cpu_usage > 85:
            alerts.append("High CPU usage")
        if self.state.latency > 300:
            alerts.append("High latency")
        if not self.state.db_connected:
            alerts.append("Database connection failure")

        return Observation(
            logs=logs,
            metrics=metrics,
            alerts=alerts,
            system_status=self._get_status(),
            step_count=self.state.step_count,
            max_steps=self.state.max_steps,
            task_id=self.state.task_id,
            description="Realistic distributed system under stress",
        )

    # -----------------------------
    # STATUS
    # -----------------------------
    def _get_status(self) -> str:
        if self.state.latency < 300 and self.state.cpu_usage < 85:
            return "healthy"
        elif self.state.latency < 500:
            return "degraded"
        else:
            return "down"

    # -----------------------------
    # LOGS
    # -----------------------------
    def _generate_logs(self):
        logs = []

        if not self.state.db_connected:
            logs.append("[ERROR] Database connection timeout")

        if not self.state.cache_clean:
            logs.append("[WARN] Cache miss rate is high")

        if self.state.cpu_usage > 85:
            logs.append("[WARN] CPU usage spike detected")

        if self.state.latency > 300:
            logs.append("[ERROR] API response latency critical")

        logs.append("[INFO] System monitoring active")

        return logs