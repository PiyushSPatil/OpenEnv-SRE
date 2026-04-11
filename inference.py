import os
import requests
from openai import OpenAI  # Always import, don't try/except

# -----------------------------
# CONFIG
# -----------------------------
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

# CRITICAL: These MUST come from environment variables
API_BASE_URL = os.getenv("API_BASE_URL")  # This is the LLM proxy URL
API_KEY = os.getenv("API_KEY")  # This is the proxy API key

MAX_STEPS = 6
ENV_NAME = "openenv_sre"

# -----------------------------
# INITIALIZE CLIENT (MANDATORY)
# -----------------------------
# The validator expects you to ALWAYS initialize the client
# Do NOT check if these exist - let it fail if missing
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
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={err}", flush=True)

def log_end(success, steps, rewards):
    total = sum(rewards)
    score = min(max(total, 0.0), 1.0)
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)

# -----------------------------
# LLM ACTION (MUST CALL PROXY)
# -----------------------------
def llm_action(obs):
    # DO NOT have fallback actions - ALWAYS call the proxy
    # If this fails, the test should fail (that's what validator wants)
    
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "You are an SRE expert. Fix the system efficiently."},
            {
                "role": "user",
                "content": f"""
Logs: {obs.get('logs', [])}
Metrics: {obs.get('metrics', {})}
Alerts: {obs.get('alerts', [])}

Choose ONE action to fix the issue:
- clear_cache
- fix_db_connection
- scale_service (target: api)
- restart_service (target: backend)

Return ONLY the action in JSON format like: {{"action_type": "restart_service", "target": "backend"}}
"""
            }
        ],
        temperature=0,
    )
    
    # Parse the response
    text = response.choices[0].message.content.strip()
    
    # Simple parsing - adjust based on actual response format
    if "fix_db_connection" in text:
        return {"action_type": "fix_db_connection", "target": None}
    elif "scale_service" in text:
        return {"action_type": "scale_service", "target": "api"}
    elif "clear_cache" in text:
        return {"action_type": "clear_cache", "target": None}
    else:
        return {"action_type": "restart_service", "target": "backend"}

# -----------------------------
# RUN TASK
# -----------------------------
def run_task(task_id):
    log_start(task_id)
    
    rewards = []
    success = False
    steps_taken = 0
    
    # Reset environment
    res = requests.post(f"{ENV_BASE_URL}/reset", json={"task_id": task_id}, timeout=10)
    data = res.json()
    
    obs = data.get("observation", {})
    done = data.get("done", False)
    
    for step in range(1, MAX_STEPS + 1):
        if done:
            break
        
        # ALWAYS call LLM through proxy
        action = llm_action(obs)
        
        # Take action in environment
        res = requests.post(f"{ENV_BASE_URL}/step", json=action, timeout=10)
        data = res.json()
        
        obs = data.get("observation", {})
        reward = round(data.get("reward", {}).get("value", 0.0), 2)
        done = data.get("done", False)
        
        rewards.append(reward)
        steps_taken = step
        
        log_step(step, action, reward, done)
        
        if obs.get("system_status") == "healthy":
            success = True
            break
    
    if obs.get("system_status") == "healthy":
        success = True
    
    log_end(success, steps_taken, rewards)

# -----------------------------
# MAIN
# -----------------------------
def main():
    for task in ["easy_cache", "medium_db", "hard_outage"]:
        run_task(task)

if __name__ == "__main__":
    main()