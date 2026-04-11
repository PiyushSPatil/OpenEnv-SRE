import os
import sys
import requests
from openai import OpenAI

# -----------------------------
# CONFIG (STRICT FOR VALIDATOR)
# -----------------------------
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
ENV_SERVER_URL = os.getenv("ENV_SERVER_URL", "http://localhost:7860")

MAX_STEPS = 6
ENV_NAME = "openenv_sre"

# -----------------------------
# 🔥 STRICT PROXY CLIENT (MANDATORY)
# -----------------------------
# Fail fast if required environment variables are missing
if "API_KEY" not in os.environ:
    print("[ERROR] API_KEY environment variable is missing", flush=True)
    sys.exit(1)
    
if "API_BASE_URL" not in os.environ:
    print("[ERROR] API_BASE_URL environment variable is missing", flush=True)
    sys.exit(1)

# Initialize client - MUST succeed
try:
    client = OpenAI(
        api_key=os.environ["API_KEY"],
        base_url=os.environ["API_BASE_URL"]
    )
    print(f"[INFO] OpenAI client initialized with base_url={os.environ['API_BASE_URL']}", flush=True)
except Exception as e:
    print(f"[ERROR] Client initialization failed: {e}", flush=True)
    sys.exit(1)

# Verify the client works by making a test call
try:
    test_response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": "test"}],
        max_tokens=1,
        temperature=0
    )
    print("[INFO] Successfully connected to LLM proxy", flush=True)
except Exception as e:
    print(f"[ERROR] Failed to connect to LLM proxy: {e}", flush=True)
    sys.exit(1)


# -----------------------------
# LOGGING
# -----------------------------
def log_start(task):
    print(f"[START] task={task} env={ENV_NAME} model={MODEL_NAME}", flush=True)


def log_step(step, action, reward, done, error=None):
    err = error if error else "null"
    # Convert action dict to string for logging
    action_str = f"{action.get('action_type', 'unknown')}:{action.get('target', 'none')}"
    print(f"[STEP] step={step} action={action_str} reward={reward:.2f} done={str(done).lower()} error={err}", flush=True)


def log_end(success, steps, rewards):
    total = sum(rewards)
    score = min(max(total, 0.0), 1.0)
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)


# -----------------------------
# 🔥 LLM ACTION (FORCES PROXY)
# -----------------------------
def llm_action(obs):
    """
    Always makes an API call through the proxy.
    No fallbacks or exception handlers that would mask proxy failures.
    """
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are an SRE expert. Respond with exactly one action from the list: clear_cache, fix_db_connection, scale_service, restart_service. Do not add any explanation."},
            {
                "role": "user",
                "content": f"""
Logs: {obs.get('logs', 'No logs available')}
Metrics: {obs.get('metrics', 'No metrics available')}
Alerts: {obs.get('alerts', 'No alerts available')}

Based on the above information, what action should be taken?
Return ONLY ONE of these exact words:
- clear_cache
- fix_db_connection
- scale_service
- restart_service
"""
            }
        ],
        temperature=0,
        max_tokens=50
    )

    text = (response.choices[0].message.content or "").lower().strip()
    print(f"[DEBUG] LLM response: {text}", flush=True)

    # Parse the response
    if "fix_db" in text or "db_connection" in text:
        return {"action_type": "fix_db_connection", "target": "database"}
    elif "scale" in text:
        return {"action_type": "scale_service", "target": "api"}
    elif "clear_cache" in text or "cache" in text:
        return {"action_type": "clear_cache", "target": "redis"}
    elif "restart" in text:
        return {"action_type": "restart_service", "target": "backend"}
    else:
        # Default action but still log what happened
        print(f"[WARN] Unrecognized LLM response: {text}, using default action", flush=True)
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
        # Reset the environment
        res = requests.post(f"{ENV_SERVER_URL}/reset", json={"task_id": task_id}, timeout=10)
        res.raise_for_status()
        data = res.json()

        obs = data.get("observation", {})
        done = data.get("done", False)

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            # 🔥 ALWAYS CALL LLM (MANDATORY)
            # No try-catch here - if this fails, the task fails
            action = llm_action(obs)

            # Execute the action in the environment
            try:
                res = requests.post(f"{ENV_SERVER_URL}/step", json=action, timeout=10)
                res.raise_for_status()
                data = res.json()
            except requests.exceptions.RequestException as e:
                log_step(step, action, 0.0, True, error=str(e))
                break

            obs = data.get("observation", {})
            reward = round(data.get("reward", {}).get("value", 0.0), 2)
            done = data.get("done", False)

            rewards.append(reward)
            steps_taken = step

            log_step(step, action, reward, done)

            # Check if system is healthy
            if obs.get("system_status") == "healthy":
                success = True
                break

        # Final check for success
        if obs.get("system_status") == "healthy":
            success = True

    except Exception as e:
        print(f"[ERROR] Task {task_id} failed: {e}", flush=True)
        log_step(0, {"action_type": "error", "target": "none"}, 0.0, True, error=str(e))

    log_end(success, steps_taken, rewards)
    return success


# -----------------------------
# MAIN
# -----------------------------
def main():
    print("[INFO] Starting inference script", flush=True)
    print(f"[INFO] Using MODEL_NAME={MODEL_NAME}", flush=True)
    print(f"[INFO] Using ENV_SERVER_URL={ENV_SERVER_URL}", flush=True)
    
    tasks = ["easy_cache", "medium_db", "hard_outage"]
    results = {}
    
    for task in tasks:
        print(f"[INFO] Running task: {task}", flush=True)
        success = run_task(task)
        results[task] = success
    
    print(f"[INFO] All tasks completed. Results: {results}", flush=True)


if __name__ == "__main__":
    main()