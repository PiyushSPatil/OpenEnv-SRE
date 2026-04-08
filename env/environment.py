from typing import Dict, Tuple

from .models import Observation, Action, Reward, StepResult, InternalState
from .simulator import SRESimulator
from .tasks import get_task, list_tasks
from .grader import SREGrader


class SREEnvironment:
    """
    OpenEnv-compatible environment for AI SRE simulation.
    """

    def __init__(self):
        self.simulator = SRESimulator()
        self.grader = SREGrader()
        self.current_task_id: str = None
        self.done: bool = False

    # -----------------------------
    # RESET
    # -----------------------------
    def reset(self, task_id: str = "easy_cache") -> Observation:
        """
        Reset environment to initial state.
        """

        if task_id not in list_tasks():
            raise ValueError(f"Invalid task_id: {task_id}")

        self.current_task_id = task_id
        self.done = False

        observation = self.simulator.reset(task_id)

        return observation

    # -----------------------------
    # STEP
    # -----------------------------
    def step(self, action: Action) -> Tuple[Observation, Reward, bool, Dict]:
        """
        Apply action to environment.
        """

        if self.done:
            raise RuntimeError("Episode already finished. Call reset().")

        observation, reward, done, info = self.simulator.step(action)

        self.done = done

        # Add final grading score when episode ends
        if done:
            final_score = self.grader.grade(self.simulator.state)
            info["final_score"] = final_score

        return observation, reward, done, info

    # -----------------------------
    # STATE
    # -----------------------------
    def state(self) -> Dict:
        """
        Returns internal state (for debugging / evaluation)
        """

        state: InternalState = self.simulator.state

        if state is None:
            return {}

        return state.dict()

    # -----------------------------
    # AVAILABLE TASKS
    # -----------------------------
    def available_tasks(self):
        """
        Returns list of available task IDs
        """
        return list_tasks()