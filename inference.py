import asyncio
import os
from typing import List, Optional

from openai import OpenAI

from env.environment import SREEnvironment
from env.models import Action, Observation, Reward

API_KEY = os.getenv("API_KEY") or os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL") or "https://router.huggingface.co/v1"
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

TASKS = ["easy_cache", "medium_db", "hard_outage"]
BENCHMARK = "openenv_sre"
MAX_STEPS = 6


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
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)


def get_action(client: OpenAI, obs: Observation) -> dict:
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
Logs: {obs.logs}
Metrics: {obs.metrics}
Alerts: {obs.alerts}

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


async def run_task(client: OpenAI, env: SREEnvironment, task: str) -> None:
    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False

    log_start(task=task, env=BENCHMARK, model=MODEL_NAME)

    try:
        obs = env.reset(task_id=task)

        for step in range(1, MAX_STEPS + 1):
            if env.done:
                break

            action_dict = get_action(client, obs)
            action = Action(**action_dict)

            obs, reward, done, info = env.step(action)

            rewards.append(reward.value)
            steps_taken = step

            log_step(step=step, action=str(action), reward=reward.value, done=done, error=None)

            if done:
                break

        score = min(max(sum(rewards), 0.0), 1.0)
        success = obs.system_status == "healthy"

    except Exception as e:
        print(f"[DEBUG] Task failed: {e}", flush=True)

    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)


async def main() -> None:
    try:
        client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    except Exception as e:
        print(f"[DEBUG] Client init failed: {e}", flush=True)
        client = None

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

    env = SREEnvironment()

    for task in TASKS:
        await run_task(client, env, task)


if __name__ == "__main__":
    asyncio.run(main())