from typing import Dict, List


# -----------------------------
# TASK DEFINITIONS
# -----------------------------
TASKS: Dict[str, Dict] = {
    "easy_cache": {
        "name": "Fix High Latency Due to Cache",
        "difficulty": "easy",
        "description": (
            "The system is experiencing high latency due to inefficient caching. "
            "Identify the issue and resolve it to restore performance."
        ),
        "goal": "Reduce latency below 150 ms",
        "max_steps": 6,
    },

    "medium_db": {
        "name": "Resolve Database Connection Failure",
        "difficulty": "medium",
        "description": (
            "The system is failing due to database connection issues. "
            "Diagnose the problem and restore database connectivity."
        ),
        "goal": "Restore database connection and reduce latency",
        "max_steps": 8,
    },

    "hard_outage": {
        "name": "Recover from Full Production Outage",
        "difficulty": "hard",
        "description": (
            "The system is facing a full production outage involving multiple failures "
            "including database failure, high CPU usage, and service crashes. "
            "Stabilize the system and restore all services."
        ),
        "goal": (
            "Fix database, reduce CPU usage, restart services, "
            "and bring system back to healthy state"
        ),
        "max_steps": 10,
    },
}


# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def get_task(task_id: str) -> Dict:
    """
    Retrieve task configuration by ID.
    """
    if task_id not in TASKS:
        raise ValueError(f"Invalid task_id: {task_id}")
    return TASKS[task_id]


def list_tasks() -> List[str]:
    """
    Return all available task IDs.
    """
    return list(TASKS.keys())


def get_task_metadata(task_id: str) -> Dict:
    """
    Returns simplified metadata for UI or logging.
    """
    task = get_task(task_id)
    return {
        "task_id": task_id,
        "name": task["name"],
        "difficulty": task["difficulty"],
        "goal": task["goal"],
    }