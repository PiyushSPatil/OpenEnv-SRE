import os
import requests
from typing import List, Optional
from openai import OpenAI

# -----------------------------
# CONFIG (STRICT)
# -----------------------------
API_BASE_URL = os.environ["API_BASE_URL"]   # 🔥 MUST
API_KEY = os.environ["API_KEY"]             # 🔥 MUST
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

MAX_STEPS = 6
ENV_NAME = "openenv_sre"

# -----------------------------
# OPENAI CLIENT (STRICT PROXY)
# -----------------------------
client = OpenAI(
    base_url=API_BASE_URL,
    api_key=API_KEY
)

# -----------------------------
# LOGGING (STRICT FORMAT)
# -----------------------------
def log_start(task):
    print(f"[START] task={task} env={ENV_NAME} model={MODEL_NAME}", flush=True)


def log_step(step, action, reward, done, error=None):
    error_val = error if error else "null"
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error_val}", flush=True)


def log_end(success, steps, rewards):
    score = min(max(sum(rewards), 0.0), 1.0)
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)


# -----------------------------
# LLM ACTION (MANDATORY)
# -----------------------------
def llm_action(obs):
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an expert SRE engineer."},
                {
                    "role": "user",
                    "content": f"""
Logs: {obs.get('logs')}
Metrics: {obs.get('metrics')}
Alerts: {obs.get('alerts')}

Choose ONE action:
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

    except Exception:
        pass

    return {"action_type": "restart_service", "target": "backend"}


# -----------------------------
# DECISION ENGINE (FORCE LLM)
# -----------------------------
def choose_action(obs, history):
    return llm_action(obs)   # 🔥 ALWAYS CALL LLM


# -----------------------------
# RUN TASK
# -----------------------------
def run_task(task_id):
    log_start(task_id)

    rewards = []
    history = []
    success = False

    try:
        res = requests.post(f"{API_BASE_URL}/reset", json={"task_id": task_id}, timeout=10)
        res.raise_for_status()
        data = res.json()

        obs = data.get("observation", {})
        done = data.get("done", False)

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            action = choose_action(obs, history)

            res = requests.post(f"{API_BASE_URL}/step", json=action, timeout=10)
            res.raise_for_status()
            data = res.json()

            obs = data.get("observation", {})
            reward = round(data.get("reward", {}).get("value", 0.0), 2)
            done = data.get("done", False)

            rewards.append(reward)
            history.append(action["action_type"])

            log_step(step, action, reward, done)

            if obs.get("system_status") == "healthy":
                success = True
                break

    except Exception as e:
        log_step(0, {"error": str(e)}, 0.0, True, error=str(e))

    log_end(success, len(rewards), rewards)


# -----------------------------
# MAIN
# -----------------------------
def main():
    for task in ["easy_cache", "medium_db", "hard_outage"]:
        run_task(task)


if __name__ == "__main__":
    main()