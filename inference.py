import os
import requests
from openai import OpenAI

# -----------------------------
# CONFIG
# -----------------------------
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")
LLM_BASE_URL = os.environ["API_BASE_URL"]   # 🔥 ALWAYS FROM EVALUATOR

MODEL_NAME = "gpt-4o-mini"
MAX_STEPS = 6
ENV_NAME = "openenv_sre"

# -----------------------------
# OPENAI CLIENT (STRICT PROXY)
# -----------------------------
client = OpenAI(
    api_key=os.environ["API_KEY"],
    base_url=LLM_BASE_URL
)

# -----------------------------
# LOGGING
# -----------------------------
def log_start(task):
    print(f"[START] task={task} env={ENV_NAME}", flush=True)


def log_step(step, action, reward, done, error=None):
    err = error if error else "null"
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={err}", flush=True)


def log_end(success, steps, rewards):
    score = min(max(sum(rewards), 0.0), 1.0)
    r = ",".join(f"{x:.2f}" for x in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={r}", flush=True)


# -----------------------------
# LLM ACTION (MANDATORY)
# -----------------------------
def llm_action(obs):
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

Choose ONE action:
clear_cache, fix_db_connection, scale_service, restart_service
"""
                }
            ],
            temperature=0
        )

        text = res.choices[0].message.content.lower()

        if "fix_db" in text:
            return {"action_type": "fix_db_connection", "target": None}
        if "scale" in text:
            return {"action_type": "scale_service", "target": "api"}
        if "clear_cache" in text:
            return {"action_type": "clear_cache", "target": None}

    except:
        pass

    return {"action_type": "restart_service", "target": "backend"}


# -----------------------------
# DECISION
# -----------------------------
def choose_action(obs, history):
    return llm_action(obs)  # 🔥 ALWAYS CALL LLM


# -----------------------------
# RUN TASK
# -----------------------------
def run_task(task):
    log_start(task)

    rewards = []
    success = False

    try:
        # 🔥 TRY ENV BASE URL FIRST
        try:
            res = requests.post(f"{ENV_BASE_URL}/reset", json={"task_id": task}, timeout=5)
            res.raise_for_status()
        except:
            # 🔥 FALLBACK TO PROXY IF NEEDED
            res = requests.post(f"{LLM_BASE_URL}/reset", json={"task_id": task})

        data = res.json()
        obs = data["observation"]
        done = data["done"]

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            action = choose_action(obs, [])

            try:
                res = requests.post(f"{ENV_BASE_URL}/step", json=action, timeout=5)
                res.raise_for_status()
            except:
                res = requests.post(f"{LLM_BASE_URL}/step", json=action)

            data = res.json()

            obs = data["observation"]
            reward = data["reward"]["value"]
            done = data["done"]

            rewards.append(reward)

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
    for t in ["easy_cache", "medium_db", "hard_outage"]:
        run_task(t)


if __name__ == "__main__":
    main()