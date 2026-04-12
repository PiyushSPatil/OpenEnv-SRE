import asyncio
import os
from typing import List, Optional

import requests
from openai import OpenAI

# -----------------------------
# CONFIG
# -----------------------------
API_KEY = os.getenv("API_KEY") or os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL")
if not API_KEY or not API_BASE_URL:
    raise RuntimeError(
        "Missing required environment variables: API_KEY and API_BASE_URL."
    )

MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")

TASKS = ["easy_cache", "medium_db", "hard_outage"]
BENCHMARK = "openenv_sre"
MAX_STEPS = 6

# -----------------------------
# LOGGING
# -----------------------------
def log_start(task, env, model):
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step, action, reward, done, error=None):
    error_val = error if error else "null"
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={error_val}",
        flush=True,
    )


def log_end(success, steps, score, rewards):
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# -----------------------------
# CLIENT INIT
# -----------------------------
def init_client():
    try:
        return OpenAI(
            base_url=API_BASE_URL,
            api_key=API_KEY,
        )
    except Exception as e:
        print(f"[DEBUG] Client init failed: {e}", flush=True)
        return None


# -----------------------------
# LLM ACTION
# -----------------------------
def get_action(client, obs):
    if not client:
        return {"action_type": "restart_service", "target": "backend"}

    try:
        res = client.chat.completions.create(
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
                },
            ],
            temperature=0,
        )

        text = (res.choices[0].message.content or "").lower()

        if "fix_db" in text:
            return {"action_type": "fix_db_connection", "target": None}
        if "scale" in text:
            return {"action_type": "scale_service", "target": "api"}
        if "clear" in text:
            return {"action_type": "clear_cache", "target": None}

    except Exception as e:
        print(f"[DEBUG] LLM failed: {e}", flush=True)

    return {"action_type": "restart_service", "target": "backend"}


# -----------------------------
# RUN TASK
# -----------------------------
async def run_task(client, task):
    log_start(task, BENCHMARK, MODEL_NAME)

    rewards = []
    steps_taken = 0
    success = False

    try:
        res = requests.post(f"{ENV_BASE_URL}/reset", json={"task_id": task}, timeout=10)
        data = res.json()

        obs = data.get("observation", {})
        done = data.get("done", False)

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            action = get_action(client, obs)

            try:
                res = requests.post(f"{ENV_BASE_URL}/step", json=action, timeout=10)
                data = res.json()
            except Exception as e:
                log_step(step, str(action), 0.0, True, str(e))
                break

            obs = data.get("observation", {})
            reward = float(data.get("reward", {}).get("value", 0.0))
            done = data.get("done", False)

            rewards.append(reward)
            steps_taken = step

            log_step(step, str(action), reward, done)

            if obs.get("system_status") == "healthy":
                success = True
                break

        if obs.get("system_status") == "healthy":
            success = True

    except Exception as e:
        log_step(0, "error", 0.0, True, str(e))

    score = min(max(sum(rewards), 0.0), 1.0)

    log_end(success, steps_taken, score, rewards)


# -----------------------------
# MAIN
# -----------------------------
async def main():
    client = init_client()

    # 🔥 TRY proxy call (no crash)
    if client:
        try:
            client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": "ping"}],
                temperature=0,
            )
        except Exception as e:
            print(f"[DEBUG] Proxy ping failed: {e}", flush=True)

    for task in TASKS:
        await run_task(client, task)


if __name__ == "__main__":
    asyncio.run(main())