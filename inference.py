import os
import requests

# -----------------------------
# SAFE OPENAI IMPORT
# -----------------------------
from openai import OpenAI

# -----------------------------
# CONFIG
# -----------------------------
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")
MODEL_NAME = "gpt-4o-mini"

MAX_STEPS = 6
ENV_NAME = "openenv_sre"

# -----------------------------
# OPENAI CLIENT (STRICT + SAFE)
# -----------------------------
client = None

try:
    api_key = os.environ.get("API_KEY")
    base_url = os.environ.get("API_BASE_URL")

    if api_key and base_url:
        client = OpenAI(
            api_key=api_key,
            base_url=base_url
        )
        print("[INFO] Using LiteLLM proxy", flush=True)
    else:
        print("[ERROR] Missing API_KEY or API_BASE_URL", flush=True)

except Exception as e:
    print(f"[CLIENT INIT ERROR] {e}", flush=True)
    client = None


# -----------------------------
# LOGGING
# -----------------------------
def log_start(task):
    print(f"[START] task={task} env={ENV_NAME} model={MODEL_NAME}", flush=True)


def log_step(step, action, reward, done, error=None):
    err = error if error else "null"
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={err}",
        flush=True,
    )


def log_end(success, steps, rewards):
    total = sum(rewards)
    score = min(max(total, 0.0), 1.0)
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)

    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True,
    )


# -----------------------------
# RULE-BASED AGENT
# -----------------------------
def rule_based(obs, history):
    metrics = obs.get("metrics", {})
    alerts = obs.get("alerts", [])
    task_id = obs.get("task_id")

    cpu = metrics.get("cpu", 0)
    latency = metrics.get("latency", 0)

    if obs.get("system_status") == "healthy":
        return {"action_type": "noop", "target": None}

    if task_id == "easy_cache" and latency > 180:
        return {"action_type": "clear_cache", "target": None}

    if task_id == "medium_db" and "Database connection failure" in alerts:
        return {"action_type": "fix_db_connection", "target": None}

    if task_id == "hard_outage":
        if "Database connection failure" in alerts:
            return {"action_type": "fix_db_connection", "target": None}
        if cpu > 80:
            return {"action_type": "scale_service", "target": "api"}
        if latency > 180:
            return {"action_type": "clear_cache", "target": None}

    return None


# -----------------------------
# SAFE FALLBACK
# -----------------------------
def safe_fallback(obs):
    alerts = obs.get("alerts", [])
    cpu = obs.get("metrics", {}).get("cpu", 0)
    latency = obs.get("metrics", {}).get("latency", 0)

    if "Database connection failure" in alerts:
        return {"action_type": "fix_db_connection", "target": None}

    if cpu > 75:
        return {"action_type": "scale_service", "target": "api"}

    if latency > 150:
        return {"action_type": "clear_cache", "target": None}

    return {"action_type": "restart_service", "target": "backend"}


# -----------------------------
# LLM ACTION (MANDATORY CALL)
# -----------------------------
def llm_action(obs):
    if client is None:
        print("[LLM ERROR] Client not initialized", flush=True)
        return None

    try:
        prompt = f"""
You are an expert Site Reliability Engineer (SRE).

Your goal is to FIX the system and make it HEALTHY.

Logs: {obs.get('logs')}
Metrics: {obs.get('metrics')}
Alerts: {obs.get('alerts')}

Rules:
- If database error → fix_db_connection
- If CPU > 80 → scale_service
- If latency > 180 → clear_cache
- Otherwise → restart_service

Respond with ONLY one action:
clear_cache, fix_db_connection, scale_service, restart_service
"""

        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an expert SRE engineer."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )

        text = (response.choices[0].message.content or "").strip().lower()
        print(f"[LLM RESPONSE] {text}", flush=True)

        if "fix_db_connection" in text:
            return {"action_type": "fix_db_connection", "target": None}
        elif "scale_service" in text:
            return {"action_type": "scale_service", "target": "api"}
        elif "clear_cache" in text:
            return {"action_type": "clear_cache", "target": None}
        elif "restart_service" in text:
            return {"action_type": "restart_service", "target": "backend"}

    except Exception as e:
        print(f"[LLM ERROR] {e}", flush=True)

    return None


# -----------------------------
# DECISION ENGINE
# -----------------------------
def choose_action(obs, history):
    action = llm_action(obs)  # ALWAYS CALL
    if action:
        return action

    action = rule_based(obs, history)
    if action:
        return action

    return safe_fallback(obs)


# -----------------------------
# RUN TASK
# -----------------------------
def run_task(task_id):
    log_start(task_id)

    rewards = []
    history = []
    success = False

    try:
        res = requests.post(f"{ENV_BASE_URL}/reset", json={"task_id": task_id}, timeout=10)
        res.raise_for_status()
        data = res.json()

        obs = data.get("observation", {})
        done = data.get("done", False)

        for step in range(1, MAX_STEPS + 1):
            if done:
                break

            action = choose_action(obs, history)

            try:
                res = requests.post(f"{ENV_BASE_URL}/step", json=action, timeout=10)
                res.raise_for_status()
                data = res.json()
            except Exception as e:
                log_step(step, {"error": str(e)}, 0.0, True, error=str(e))
                break

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