import asyncio
import os
from typing import List, Optional

import requests
from openai import OpenAI

# -----------------------------
# CONFIG (STRICT LIKE SAMPLE)
# -----------------------------
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")

TASKS = ["easy_cache", "medium_db", "hard_outage"]
BENCHMARK = "openenv_sre"
MAX_STEPS = 6
SUCCESS_SCORE_THRESHOLD = 0.1

# -----------------------------
# LOGGING (EXACT FORMAT)
# -----------------------------
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# -----------------------------
# 🔥 YOUR SRE LOGIC (LLM)
# -----------------------------
def get_action(client: OpenAI, obs) -> dict:
    try:
        completion = client.chat.completions.create(
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
                },
            ],
            temperature=0,
        )

        text = (completion.choices[0].message.content or "").lower()

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
# RUN TASK (SYNC ENV INSIDE ASYNC)
# -----------------------------
async def run_task(client: OpenAI, task: str):
    log_start(task=task, env=BENCHMARK, model=MODEL_NAME)

    rewards: List[float] = []
    steps_taken = 0
    success = False

    try:
        # RESET
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

            log_step(step, str(action), reward, done, None)

            if obs.get("system_status") == "healthy":
                success = True
                break

        if obs.get("system_status") == "healthy":
            success = True

    except Exception as e:
        log_step(0, "error", 0.0, True, str(e))

    # SCORE NORMALIZATION
    total = sum(rewards)
    score = min(max(total, 0.0), 1.0)

    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


# -----------------------------
# MAIN (STRICT SAMPLE STYLE)
# -----------------------------
async def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    # 🔥 IMPORTANT: FORCE PROXY CALL
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