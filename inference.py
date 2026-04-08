import os
import requests
from typing import List
from openai import OpenAI

# -----------------------------
# CONFIG
# -----------------------------
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:7860")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
HF_TOKEN = os.getenv("HF_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
API_KEY = HF_TOKEN or OPENAI_API_KEY

MAX_STEPS = 6
ENV_NAME = "openenv_sre"

# -----------------------------
# OPENAI CLIENT
# -----------------------------
client = None
if API_KEY:
    client = OpenAI(api_key=API_KEY)


# -----------------------------
# LOGGING (STRICT FORMAT)
# -----------------------------
def log_start(task):
    print(f"[START] task={task} env={ENV_NAME} model={MODEL_NAME}", flush=True)


def log_step(step, action, reward, done, error=None):
    error_val = error if error else "null"
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error_val}",
        flush=True,
    )


def log_end(success, steps, rewards):
    total = sum(rewards)

    # ✅ Better scoring
    score = min(max(total, 0.0), 1.0)

    rewards_str = ",".join(f"{r:.2f}" for r in rewards)

    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# -----------------------------
# RULE-BASED AGENT (PRIMARY)
# -----------------------------
def rule_based(obs, history):
    metrics = obs.get("metrics", {})
    alerts = obs.get("alerts", [])
    task_id = obs.get("task_id")

    cpu = metrics.get("cpu", 0)
    latency = metrics.get("latency", 0)

    # STOP if healthy
    if obs.get("system_status") == "healthy":
        return {"action_type": "noop", "target": None}

    # EASY
    if task_id == "easy_cache":
        if latency > 180 and "clear_cache" not in history:
            return {"action_type": "clear_cache", "target": None}
        return None

    # MEDIUM
    if task_id == "medium_db":
        if "Database connection failure" in alerts and "fix_db_connection" not in history:
            return {"action_type": "fix_db_connection", "target": None}
        if "fix_db_connection" in history and latency > 180 and "clear_cache" not in history:
            return {"action_type": "clear_cache", "target": None}
        return None

    # HARD
    if task_id == "hard_outage":
        if "Database connection failure" in alerts and "fix_db_connection" not in history:
            return {"action_type": "fix_db_connection", "target": None}
        if cpu > 80 and history.count("scale_service") < 2:
            return {"action_type": "scale_service", "target": "api"}
        if latency > 180 and "clear_cache" not in history:
            return {"action_type": "clear_cache", "target": None}
        return None

    return None


# -----------------------------
# SAFE FALLBACK (ALWAYS WORKS)
# -----------------------------
def safe_fallback(obs, history):
    alerts = obs.get("alerts", [])
    cpu = obs["metrics"]["cpu"]
    latency = obs["metrics"]["latency"]

    if "Database connection failure" in alerts:
        return {"action_type": "fix_db_connection", "target": None}

    if cpu > 85:
        return {"action_type": "scale_service", "target": "api"}

    if latency > 300:
        return {"action_type": "clear_cache", "target": None}

    return {"action_type": "restart_service", "target": "backend"}


# -----------------------------
# LLM FALLBACK
# -----------------------------
def llm_action(obs):
    if not client:
        return None

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an expert SRE engineer."},
                {
                    "role": "user",
                    "content": f"""
Logs: {obs['logs']}
Metrics: {obs['metrics']}
Alerts: {obs['alerts']}

Choose ONE action:
clear_cache, fix_db_connection, scale_service, restart_service, noop
""",
                },
            ],
            temperature=0,
        )

        text = (response.choices[0].message.content or "").lower()

        if "fix_db" in text:
            return {"action_type": "fix_db_connection", "target": None}
        if "scale" in text:
            return {"action_type": "scale_service", "target": "api"}
        if "clear_cache" in text:
            return {"action_type": "clear_cache", "target": None}
        if "restart" in text:
            return {"action_type": "restart_service", "target": "backend"}

    except Exception:
        pass

    return None


# -----------------------------
# FINAL DECISION ENGINE
# -----------------------------
def choose_action(obs, history):
    action = rule_based(obs, history)
    if action:
        return action

    action = llm_action(obs)
    if action:
        return action

    return safe_fallback(obs, history)


# -----------------------------
# RUN TASK
# -----------------------------
def run_task(task_id):
    log_start(task_id)

    rewards = []
    history = []
    success = False
    steps_taken = 0

    try:
        res = requests.post(f"{API_BASE_URL}/reset", json={"task_id": task_id})
        data = res.json()

        obs = data["observation"]
        done = data["done"]

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            action = choose_action(obs, history)

            res = requests.post(f"{API_BASE_URL}/step", json=action)
            data = res.json()

            obs = data["observation"]
            reward = round(data["reward"]["value"], 2)
            done = data["done"]

            rewards.append(reward)
            history.append(action["action_type"])
            steps_taken = step

            log_step(step, action, reward, done)

            if obs.get("system_status") == "healthy":
                success = True
                break

        if obs.get("system_status") == "healthy":
            success = True

    except Exception as e:
        log_step(steps_taken, {"error": str(e)}, 0.0, True, error=str(e))

    log_end(success, steps_taken, rewards)


# -----------------------------
# MAIN
# -----------------------------
def main():
    tasks = ["easy_cache", "medium_db", "hard_outage"]

    for task in tasks:
        run_task(task)


if __name__ == "__main__":
    main()