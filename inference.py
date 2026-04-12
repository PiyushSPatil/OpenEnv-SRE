import os
import sys
import requests
from openai import OpenAI

# -----------------------------
# CONFIG - MUST USE PROVIDED PROXY
# -----------------------------
# CRITICAL: Use EXACT environment variables as required by validator
HF_TOKEN = os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")

MAX_STEPS = 6
ENV_NAME = "openenv_sre"

# -----------------------------
# VALIDATE SETUP - CRASH IF MISSING
# -----------------------------
def validate_setup():
    """Verify all required environment variables are present and proxy works"""
    missing = []
    
    if not HF_TOKEN:
        missing.append("HF_TOKEN")
    if not API_BASE_URL:
        missing.append("API_BASE_URL")
    
    if missing:
        print(f"[ERROR] Missing required environment variables: {', '.join(missing)}", flush=True)
        print("[ERROR] The validator injects these at runtime. Make sure you're not overriding them.", flush=True)
        return False
    
    print(f"[INFO] HF_TOKEN present: {HF_TOKEN[:10]}...", flush=True)
    print(f"[INFO] API_BASE_URL: {API_BASE_URL}", flush=True)
    print(f"[INFO] MODEL_NAME: {MODEL_NAME}", flush=True)
    
    return True

# -----------------------------
# INIT CLIENT - MUST SUCCEED
# -----------------------------
client = None

def init_client():
    global client
    try:
        client = OpenAI(
            api_key=HF_TOKEN,
            base_url=API_BASE_URL
        )
        # Test the connection with a lightweight call
        # This ensures the proxy is actually reachable
        client.models.list()
        print("[INFO] OpenAI client initialized successfully and connected to proxy", flush=True)
        return True
    except Exception as e:
        print(f"[ERROR] Client init failed: {e}", flush=True)
        print(f"[ERROR] Cannot connect to LiteLLM proxy at {API_BASE_URL}", flush=True)
        return False

# -----------------------------
# LOGGING - EXACT FORMAT REQUIRED
# -----------------------------
def log_start(task):
    print(f"[START] task={task} env={ENV_NAME} model={MODEL_NAME}", flush=True)

def log_step(step, action, reward, done, error=None):
    err = error if error else "null"
    # Convert action dict to string representation
    action_str = str(action).replace("'", '"')
    print(
        f"[STEP] step={step} action={action_str} reward={reward:.2f} done={str(done).lower()} error={err}",
        flush=True
    )

def log_end(success, steps, rewards):
    total = sum(rewards) if rewards else 0.0
    score = min(max(total, 0.0), 1.0)
    rewards_str = ",".join(f"{r:.2f}" for r in rewards) if rewards else ""
    
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True
    )

# -----------------------------
# LLM ACTION - MUST CALL PROXY EVERY TIME
# -----------------------------
def llm_action(obs, step_num, task_id):
    """Make LLM call through the proxy - NO FALLBACK ACTIONS"""
    
    if client is None:
        error_msg = "Client not initialized - cannot make LLM call"
        print(f"[ERROR] {error_msg}", flush=True)
        raise RuntimeError(error_msg)
    
    # Format the observation for the LLM
    logs = obs.get('logs', 'No logs available')
    metrics = obs.get('metrics', 'No metrics available')
    alerts = obs.get('alerts', 'No alerts active')
    system_status = obs.get('system_status', 'unknown')
    
    # Create a more detailed prompt
    prompt = f"""You are an SRE expert managing a production system.

Current System Status: {system_status}

Recent Logs:
{logs}

Current Metrics:
{metrics}

Active Alerts:
{alerts}

Task: {task_id}

Based on the current system state, choose ONE action to resolve the issue:
- clear_cache: Clear the application cache (use when cache-related issues)
- fix_db_connection: Repair database connection issues (use when DB errors)
- scale_service: Scale up a service (use when high load/service degraded)
- restart_service: Restart a service (use when service is unresponsive)

Return ONLY the action name, nothing else.
"""
    
    try:
        # Make the API call through the proxy
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an SRE expert. Return only the action name."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low temperature for deterministic responses
            max_tokens=20     # Keep response short
        )
        
        # Extract the action
        text = (response.choices[0].message.content or "").strip().lower()
        print(f"[INFO] LLM response (step {step_num}): {text}", flush=True)
        
        # Parse the response
        if "clear_cache" in text:
            return {"action_type": "clear_cache", "target": None}
        elif "fix_db" in text or "database" in text:
            return {"action_type": "fix_db_connection", "target": None}
        elif "scale" in text:
            return {"action_type": "scale_service", "target": "api"}
        elif "restart" in text:
            return {"action_type": "restart_service", "target": "backend"}
        else:
            # Default to restart if unclear - but this still counts as an API call
            print(f"[WARNING] Unclear LLM response: {text}, defaulting to restart_service", flush=True)
            return {"action_type": "restart_service", "target": "backend"}
            
    except Exception as e:
        # Log the error but don't silently fall back
        print(f"[ERROR] LLM call failed at step {step_num}: {e}", flush=True)
        # Re-raise to make the failure visible to validator
        raise RuntimeError(f"LLM API call failed: {e}")

# -----------------------------
# RUN TASK
# -----------------------------
def run_task(task_id):
    log_start(task_id)
    
    rewards = []
    success = False
    steps_taken = 0
    last_error = None
    
    try:
        # Reset the environment
        reset_response = requests.post(
            f"{ENV_BASE_URL}/reset", 
            json={"task_id": task_id}, 
            timeout=10
        )
        reset_response.raise_for_status()
        data = reset_response.json()
        
        obs = data.get("observation", {})
        done = data.get("done", False)
        
        # Main episode loop
        for step in range(1, MAX_STEPS + 1):
            if done:
                break
            
            # ALWAYS call LLM through proxy - this MUST happen every step
            try:
                action = llm_action(obs, step, task_id)
            except Exception as e:
                # LLM call failed - log as error and break
                last_error = str(e)
                log_step(step, {"action_type": "error"}, 0.0, True, error=last_error)
                break
            
            # Take action in environment
            try:
                step_response = requests.post(
                    f"{ENV_BASE_URL}/step", 
                    json=action, 
                    timeout=10
                )
                step_response.raise_for_status()
                data = step_response.json()
            except requests.exceptions.RequestException as e:
                last_error = f"Environment step failed: {e}"
                log_step(step, action, 0.0, True, error=last_error)
                break
            
            obs = data.get("observation", {})
            reward_dict = data.get("reward", {})
            reward = float(reward_dict.get("value", 0.0)) if isinstance(reward_dict, dict) else float(reward_dict)
            done = data.get("done", False)
            
            rewards.append(reward)
            steps_taken = step
            
            log_step(step, action, reward, done)
            
            # Check for success condition
            if obs.get("system_status") == "healthy":
                success = True
                break
        
        # Final success check if loop ended without success
        if not success and obs.get("system_status") == "healthy":
            success = True
            
    except requests.exceptions.RequestException as e:
        last_error = f"Environment connection failed: {e}"
        print(f"[ERROR] {last_error}", flush=True)
        log_step(0, {"action_type": "error"}, 0.0, True, error=last_error)
    except Exception as e:
        last_error = f"Unexpected error: {e}"
        print(f"[ERROR] {last_error}", flush=True)
        log_step(0, {"action_type": "error"}, 0.0, True, error=last_error)
    
    log_end(success, steps_taken, rewards)

# -----------------------------
# MAIN
# -----------------------------
def main():
    print("[INFO] Starting inference script", flush=True)
    
    # Validate setup before proceeding
    if not validate_setup():
        print("[ERROR] Setup validation failed. Exiting.", flush=True)
        sys.exit(1)
    
    # Initialize client
    if not init_client():
        print("[ERROR] Client initialization failed. Exiting.", flush=True)
        sys.exit(1)
    
    # Run all tasks
    tasks = ["easy_cache", "medium_db", "hard_outage"]
    
    for task in tasks:
        print(f"\n[INFO] Running task: {task}", flush=True)
        run_task(task)
        print(f"[INFO] Completed task: {task}\n", flush=True)
    
    print("[INFO] All tasks completed", flush=True)

if __name__ == "__main__":
    main()