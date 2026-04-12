import os
import requests
from openai import OpenAI

# -----------------------------
# CONFIG (VALIDATOR MANDATORY)
# -----------------------------
# Use the exact environment variables injected by the platform
API_KEY = os.environ.get("API_KEY")
API_BASE_URL = os.environ.get("API_BASE_URL")
MODEL_NAME = os.environ.get("MODEL_NAME", "gpt-4") # Fallback to a standard name if missing

ENV_BASE_URL = os.environ.get("ENV_BASE_URL", "http://localhost:7860")
MAX_STEPS = 6
ENV_NAME = "openenv_sre"

# -----------------------------
# CLIENT INITIALIZATION
# -----------------------------
# The validator requires base_url=os.environ["API_BASE_URL"]
if not API_KEY or not API_BASE_URL:
    raise RuntimeError("MISSING CRITICAL CREDENTIALS: API_KEY or API_BASE_URL not found in environment.")

client = OpenAI(
    api_key=API_KEY,
    base_url=API_BASE_URL
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
# LLM ACTION
# -----------------------------
def llm_action(obs):
    try:
        # All requests here will go through the LiteLLM proxy via the base_url set above
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an SRE expert. Respond with action only."},
                {
                    "role": "user",
                    "content": f"Logs: {obs.get('logs')}\nMetrics: {obs.get('metrics')}\nAlerts: {obs.get('alerts')}\n\nReturn ONE: clear_cache, fix_db_connection, scale_service, restart_service"
                }
            ],
            temperature=0,
        )

        text = (response.choices[0].message.content or "").lower()

        if "fix_db" in text:
            return {"action_type": "fix_db_connection", "target": None}
        if "scale" in text:
            return {"action_type": "scale_service", "target": "api"}
        if "clear" in text:
            return {"action_type": "clear_cache", "target": None}
            
    except Exception as e:
        print(f"[ERROR] Proxy LLM call failed: {e}", flush=True)

    # Only fall back if the network call actually happens and fails
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
        res = requests.post(f"{ENV_BASE_URL}/reset", json={"task_id": task_id}, timeout=10)
        data = res.json()
        obs = data.get("observation", {})
        done = data.get("done", False)

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            action = llm_action(obs)
            
            try:
                res = requests.post(f"{ENV_BASE_URL}/step", json=action, timeout=10)
                data = res.json()
            except Exception as e:
                log_step(step, action, 0.0, True, error=str(e))
                break

            obs = data.get("observation", {})
            reward = round(data.get("reward", {}).get("value", 0.0), 2)
            done = data.get("done", False)

            rewards.append(reward)
            steps_taken = step
            log_step(step, action, reward, done)

            if obs.get("system_status") == "healthy":
                success = True
                break

    except Exception as e:
        print(f"[ERROR] Task execution error: {e}", flush=True)

    log_end(success, steps_taken, rewards)

def main():
    tasks = ["easy_cache", "medium_db", "hard_outage"]
    for task in tasks:
        run_task(task)

if __name__ == "__main__":
    main()
