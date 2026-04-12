#!/usr/bin/env python3
import os
import sys
import json
import time
import requests
import traceback
from typing import Dict, Any, Optional
from openai import OpenAI

# -----------------------------
# CONFIGURATION
# -----------------------------
# LLM Configuration (MUST use proxy)
HF_TOKEN = os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

# Environment Configuration (Your HF Space URL)
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")

MAX_STEPS = 10
ENV_NAME = "openenv_sre"
TIMEOUT = 30

# -----------------------------
# VALIDATE SETUP
# -----------------------------
def validate_setup():
    """Verify all required environment variables are present"""
    missing = []
    
    if not HF_TOKEN:
        missing.append("HF_TOKEN")
    if not API_BASE_URL:
        missing.append("API_BASE_URL")
    
    if missing:
        print(f"[ERROR] Missing required environment variables: {', '.join(missing)}", flush=True)
        return False
    
    # Don't print full token for security
    token_preview = HF_TOKEN[:10] + "..." if len(HF_TOKEN) > 10 else "***"
    print(f"[INFO] API_BASE_URL: {API_BASE_URL}", flush=True)
    print(f"[INFO] MODEL_NAME: {MODEL_NAME}", flush=True)
    print(f"[INFO] ENV_BASE_URL: {ENV_BASE_URL}", flush=True)
    print(f"[INFO] HF_TOKEN: {token_preview}", flush=True)
    
    return True

# -----------------------------
# INIT OPENAI CLIENT
# -----------------------------
client = None

def init_client():
    global client
    try:
        client = OpenAI(
            api_key=HF_TOKEN,
            base_url=API_BASE_URL,
            timeout=30.0
        )
        # Test connection to proxy
        client.models.list()
        print("[INFO] OpenAI client initialized successfully and connected to proxy", flush=True)
        return True
    except Exception as e:
        print(f"[ERROR] Client init failed: {e}", flush=True)
        return False

# -----------------------------
# LOGGING (EXACT FORMAT)
# -----------------------------
def log_start(task):
    print(f"[START] task={task} env={ENV_NAME} model={MODEL_NAME}", flush=True)

def log_step(step, action, reward, done, error=None):
    error_str = error if error else "null"
    # Ensure action is JSON serializable
    if isinstance(action, dict):
        action_str = json.dumps(action)
    else:
        action_str = str(action).replace("'", '"')
    
    print(
        f"[STEP] step={step} action={action_str} reward={reward:.2f} done={str(done).lower()} error={error_str}",
        flush=True
    )

def log_end(success, steps, rewards, score=None):
    if score is None and rewards:
        score = min(sum(rewards) / len(rewards), 1.0)
    elif score is None:
        score = 0.0
    
    rewards_str = ",".join(f"{r:.2f}" for r in rewards) if rewards else ""
    
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}",
        flush=True
    )

# -----------------------------
# ENVIRONMENT API CALLS
# -----------------------------
def reset_environment(task_id: str) -> Optional[Dict]:
    """Call reset endpoint on HF Space"""
    try:
        response = requests.post(
            f"{ENV_BASE_URL}/reset",
            json={"task_id": task_id},
            timeout=TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        data = response.json()
        print(f"[INFO] Reset successful for task: {task_id}", flush=True)
        return data
    except requests.exceptions.ConnectionError:
        print(f"[ERROR] Cannot connect to environment at {ENV_BASE_URL}", flush=True)
        return None
    except requests.exceptions.Timeout:
        print(f"[ERROR] Timeout connecting to environment at {ENV_BASE_URL}", flush=True)
        return None
    except Exception as e:
        print(f"[ERROR] Reset failed: {e}", flush=True)
        return None

def step_environment(action: Dict) -> Optional[Dict]:
    """Call step endpoint on HF Space"""
    try:
        response = requests.post(
            f"{ENV_BASE_URL}/step",
            json=action,
            timeout=TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"[ERROR] Step failed: {e}", flush=True)
        return None

# -----------------------------
# LLM ACTION (MUST USE PROXY)
# -----------------------------
def get_llm_action(observation: Dict, step_num: int, task_id: str) -> Dict:
    """Get action from LLM through the proxy"""
    
    if client is None:
        raise RuntimeError("OpenAI client not initialized")
    
    # Extract observation data safely
    logs = observation.get('logs', [])
    if isinstance(logs, list):
        logs_text = "\n".join(logs[-5:]) if logs else "No logs"
    else:
        logs_text = str(logs)
    
    metrics = observation.get('metrics', {})
    if isinstance(metrics, dict):
        metrics_text = ", ".join([f"{k}={v}" for k, v in metrics.items()])
    else:
        metrics_text = str(metrics)
    
    alerts = observation.get('alerts', [])
    if isinstance(alerts, list):
        alerts_text = ", ".join(alerts) if alerts else "None"
    else:
        alerts_text = str(alerts)
    
    system_status = observation.get('system_status', 'unknown')
    max_steps = observation.get('max_steps', MAX_STEPS)
    
    prompt = f"""You are an SRE expert managing a production system.

Current System Status: {system_status}
Task: {task_id}
Step: {step_num}/{max_steps}

Recent Logs:
{logs_text}

Current Metrics:
{metrics_text}

Active Alerts:
{alerts_text}

Choose ONE action from these options:
- restart_service (target: backend, frontend, database)
- scale_service (target: api, worker, backend)
- clear_cache (target: cache, redis)
- fix_db_connection (no target needed)
- noop (do nothing)

Return ONLY JSON: {{"action_type": "...", "target": "..."}}
Example: {{"action_type": "restart_service", "target": "backend"}}
Example: {{"action_type": "clear_cache", "target": "cache"}}
Example: {{"action_type": "fix_db_connection", "target": null}}

Action:"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an SRE expert. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=50
        )
        
        # Parse response
        text = response.choices[0].message.content
        print(f"[INFO] LLM response: {text}", flush=True)
        
        # Parse JSON
        try:
            # Extract JSON if wrapped in markdown
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            action_data = json.loads(text.strip())
        except json.JSONDecodeError:
            # Fallback: extract action from text
            text_lower = text.lower()
            if "restart" in text_lower:
                action_data = {"action_type": "restart_service", "target": "backend"}
            elif "scale" in text_lower:
                action_data = {"action_type": "scale_service", "target": "api"}
            elif "clear" in text_lower or "cache" in text_lower:
                action_data = {"action_type": "clear_cache", "target": "cache"}
            elif "fix" in text_lower or "db" in text_lower:
                action_data = {"action_type": "fix_db_connection", "target": None}
            else:
                action_data = {"action_type": "restart_service", "target": "backend"}
        
        # Ensure required fields
        if "action_type" not in action_data:
            action_data["action_type"] = "restart_service"
        if "target" not in action_data:
            action_data["target"] = None
            
        return action_data
        
    except Exception as e:
        print(f"[ERROR] LLM call failed: {e}", flush=True)
        raise

# -----------------------------
# RUN TASK
# -----------------------------
def run_task(task_id: str):
    """Run a single task episode"""
    log_start(task_id)
    
    rewards = []
    steps_taken = 0
    success = False
    final_score = 0.0
    observation = {}
    info = {}  # Initialize info to empty dict
    
    # Reset environment
    reset_data = reset_environment(task_id)
    if reset_data is None:
        log_end(False, 0, [], 0.0)
        return
    
    observation = reset_data.get('observation', {})
    done = reset_data.get('done', False)
    max_steps = observation.get('max_steps', MAX_STEPS)
    
    # Episode loop
    for step in range(1, max_steps + 1):
        if done:
            break
        
        # Get action from LLM (MUST go through proxy)
        try:
            action = get_llm_action(observation, step, task_id)
        except Exception as e:
            error_msg = f"LLM action failed: {e}"
            log_step(step, {"action_type": "error"}, 0.0, True, error=error_msg)
            break
        
        # Execute step
        step_data = step_environment(action)
        if step_data is None:
            error_msg = "Environment step failed - no response"
            log_step(step, action, 0.0, True, error=error_msg)
            break
        
        # Extract data
        observation = step_data.get('observation', {})
        reward_dict = step_data.get('reward', {})
        
        if isinstance(reward_dict, dict):
            reward_value = float(reward_dict.get('value', 0.0))
        elif isinstance(reward_dict, (int, float)):
            reward_value = float(reward_dict)
        else:
            reward_value = 0.0
        
        done = step_data.get('done', False)
        info = step_data.get('info', {})  # Update info
        
        rewards.append(reward_value)
        steps_taken = step
        
        log_step(step, action, reward_value, done)
        
        # Check for success
        if observation.get('system_status') == 'healthy':
            success = True
            break
    
    # Get final score from info if available
    if info and 'final_score' in info:
        final_score = info['final_score']
    elif rewards:
        final_score = min(sum(rewards) / len(rewards), 1.0)
    
    log_end(success, steps_taken, rewards, final_score)

# -----------------------------
# HEALTH CHECK
# -----------------------------
def health_check():
    """Check if environment is reachable"""
    try:
        response = requests.get(f"{ENV_BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print(f"[INFO] Environment health check passed", flush=True)
            return True
    except:
        pass
    
    # Try reset as health check
    try:
        response = requests.post(f"{ENV_BASE_URL}/reset", json={"task_id": "easy_cache"}, timeout=5)
        if response.status_code == 200:
            print(f"[INFO] Environment responding to reset", flush=True)
            return True
    except:
        pass
    
    print(f"[WARN] Cannot reach environment at {ENV_BASE_URL}", flush=True)
    return False

# -----------------------------
# MAIN
# -----------------------------
def main():
    print("[INFO] Starting inference script", flush=True)
    
    # Validate LLM setup
    if not validate_setup():
        print("[ERROR] LLM setup validation failed", flush=True)
        sys.exit(1)
    
    # Initialize LLM client
    if not init_client():
        print("[ERROR] LLM client initialization failed", flush=True)
        print("[ERROR] Make sure you have a valid HF_TOKEN", flush=True)
        sys.exit(1)
    
    # Check environment health
    health_check()
    
    # Run tasks
    tasks = ["easy_cache", "medium_db", "hard_outage"]
    
    for task in tasks:
        print(f"\n{'='*50}", flush=True)
        print(f"[INFO] Running task: {task}", flush=True)
        print(f"{'='*50}", flush=True)
        
        try:
            run_task(task)
        except Exception as e:
            print(f"[ERROR] Task {task} failed: {e}", flush=True)
            traceback.print_exc()
            # Log error end
            print(f"[END] success=false steps=0 score=0.00 rewards=", flush=True)
        
        # Small delay between tasks
        time.sleep(1)
    
    print("[INFO] All tasks completed", flush=True)
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user", flush=True)
        sys.exit(0)
    except Exception as e:
        print(f"[FATAL] Unhandled exception: {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)