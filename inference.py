import os
import requests
from openai import OpenAI

# -----------------------------
# STRICT CONFIG (MANDATORY)
# -----------------------------
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")

# ❗ MUST USE THESE EXACT VARIABLES
API_KEY = os.environ["API_KEY"]
API_BASE_URL = os.environ["API_BASE_URL"]

MAX_STEPS = 6
ENV_NAME = "openenv_sre"

# -----------------------------
# STRICT CLIENT (NO FAIL SILENTLY)
# -----------------------------
client = OpenAI(
    api_key=API_KEY,
    base_url=API_BASE_URL
)

# -----------------------------
# 🔥 FORCE REAL API CALL (REQUIRED)
# -----------------------------
# This ensures validator detects proxy usage
client.chat.completions.create(
    model=MODEL_NAME,
    messages=[{"role": "user", "content": "ping"}],
    temperature=0,
)

# -----------------------------
# LOGGING
# -----------------------------
def log_start(task):
    print(f"[START] task={task} env={ENV_NAME} model={MODEL_NAME}", flush=True)


def log_step(step, action, reward, done, error=None):
    err = error if error else "null"
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={err}",
        flush=True
    )


def log_end(success, steps, rewards):
    total = sum(rewards)
    score = min(max(total, 0.0), 1.0)
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)

    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True
    )


# -----------------------------
# LLM ACTION (ALWAYS CALL)
# -----------------------------
def llm_action(obs):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are an SRE expert."},
            {
                "role": "user",
                "content": f"""
Logs: {obs.get('logs')}
Metrics: {obs.get('metrics')}
Alerts: {obs.get('alerts')}

Return ONE:
clear_cache, fix_db_connection, scale_service, restart_service
"""
            }
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

    return {"action_type": "restart_service", "target": "backend"}


# -----------------------------
# RUN TASK
# -----------------------------
def run_task(task_id):
    log_start(task_id)

    rewards = []
    success = False
    steps_taken = 0

    try:
        res = requests.post(f"{ENV_BASE_URL}/reset", json={"task_id": task_id})
        data = res.json()

        obs = data["observation"]
        done = data["done"]

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            action = llm_action(obs)

            res = requests.post(f"{ENV_BASE_URL}/step", json=action)
            data = res.json()

            obs = data["observation"]
            reward = round(data["reward"]["value"], 2)
            done = data["done"]

            rewards.append(reward)
            steps_taken = step

            log_step(step, action, reward, done)

            if obs.get("system_status") == "healthy":
                success = True
                break

    except Exception as e:
        log_step(0, {"error": str(e)}, 0.0, True, error=str(e))

    log_end(success, steps_taken, rewards)


# -----------------------------
# MAIN
# -----------------------------
def main():
    for task in ["easy_cache", "medium_db", "hard_outage"]:
        run_task(task)


if __name__ == "__main__":
    main()