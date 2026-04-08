from typing import Dict

from .models import InternalState


class SREGrader:
    """
    Evaluates agent performance for different tasks.
    Returns a score between 0.0 and 1.0
    """

    # -----------------------------
    # MAIN ENTRY
    # -----------------------------
    def grade(self, state: InternalState) -> float:
        """
        Route grading based on task_id
        """
        if state.task_id == "easy_cache":
            return self._grade_easy_cache(state)

        elif state.task_id == "medium_db":
            return self._grade_medium_db(state)

        elif state.task_id == "hard_outage":
            return self._grade_hard_outage(state)

        else:
            raise ValueError(f"Unknown task_id: {state.task_id}")

    # -----------------------------
    # EASY TASK GRADER
    # -----------------------------
    def _grade_easy_cache(self, state: InternalState) -> float:
        """
        Goal:
        - Reduce latency < 150
        - Cache should be clean
        """

        score = 0.0

        # Cache fixed
        if state.cache_clean:
            score += 0.4

        # Latency improvement
        if state.latency < 200:
            score += 0.3

        if state.latency < 150:
            score += 0.3

        return round(min(score, 1.0), 3)

    # -----------------------------
    # MEDIUM TASK GRADER
    # -----------------------------
    def _grade_medium_db(self, state: InternalState) -> float:
        """
        Goal:
        - Restore DB connection
        - Improve latency
        """

        score = 0.0

        # DB fixed
        if state.db_connected:
            score += 0.5

        # Latency improvement
        if state.latency < 300:
            score += 0.2

        if state.latency < 200:
            score += 0.2

        # Bonus for efficiency
        if state.step_count <= state.max_steps // 2:
            score += 0.1

        return round(min(score, 1.0), 3)

    # -----------------------------
    # HARD TASK GRADER
    # -----------------------------
    def _grade_hard_outage(self, state: InternalState) -> float:
        """
        Goal:
        - Fix DB
        - Clean cache
        - Restart services
        - Reduce CPU + latency
        """

        score = 0.0

        # DB recovery
        if state.db_connected:
            score += 0.25

        # Cache fix
        if state.cache_clean:
            score += 0.15

        # Services recovery
        if all(state.services_running.values()):
            score += 0.2

        # CPU optimization
        if state.cpu_usage < 80:
            score += 0.1

        if state.cpu_usage < 60:
            score += 0.1

        # Latency improvement
        if state.latency < 300:
            score += 0.1

        if state.latency < 150:
            score += 0.1

        return round(min(score, 1.0), 3)

    # -----------------------------
    # OPTIONAL: DEBUG INFO
    # -----------------------------
    def explain_score(self, state: InternalState) -> Dict:
        """
        Returns detailed breakdown for debugging or UI
        """

        return {
            "task_id": state.task_id,
            "db_connected": state.db_connected,
            "cache_clean": state.cache_clean,
            "services_running": state.services_running,
            "cpu_usage": state.cpu_usage,
            "latency": state.latency,
            "step_count": state.step_count,
        }