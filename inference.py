import os
import sys
from typing import Dict, Any
from openai import OpenAI

# Import your environment and models
from env.environment import SREEnvironment
from env.models import Action, Observation
from env.tasks import list_tasks

# -----------------------------
# CONFIG - MUST USE PROVIDED PROXY
# -----------------------------
HF_TOKEN = os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

MAX_STEPS = 10  # Maximum for hard task
ENV_NAME = "openenv_sre"

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
        print("[ERROR] The validator injects these at runtime.", flush=True)
        return False
    
    print(f"[INFO] API_BASE_URL: {API_BASE_URL}", flush=True)
    print(f"[INFO] MODEL_NAME: {MODEL_NAME}", flush=True)
    print(f"[INFO] HF_TOKEN present: {HF_TOKEN[:20]}...", flush=True)
    
    return True

# -----------------------------
# INIT CLIENT
# -----------------------------
client = None

def init_client():
    global client
    try:
        client = OpenAI(
            api_key=HF_TOKEN,
            base_url=API_BASE_URL
        )
        # Test the connection - this proves we're using the proxy
        client.models.list()
        print("[INFO] OpenAI client initialized successfully and connected to proxy", flush=True)
        return True
    except Exception as e:
        print(f"[ERROR] Client init failed: {e}", flush=True)
        print(f"[ERROR] Could not connect to LiteLLM proxy at {API_BASE_URL}", flush=True)
        return False

# -----------------------------
# LOGGING - EXACT FORMAT
# -----------------------------
def log_start(task):
    print(f"[START] task={task} env={ENV_NAME} model={MODEL_NAME}", flush=True)

def log_step(step, action, reward, done, error=None):
    err = error if error else "null"
    # Convert action to string representation
    if isinstance(action, Action):
        action_str = f'{{"action_type": "{action.action_type}", "target": {action.target}}}'
    else:
        action_str = str(action).replace("'", '"')
    
    print(
        f"[STEP] step={step} action={action_str} reward={reward:.2f} done={str(done).lower()} error={err}",
        flush=True
    )

def log_end(success, steps, rewards):
    total_score = 0.0
    if rewards:
        # The final score might come from the grader
        # For now, use average or sum capped at 1.0
        total_score = min(sum(rewards) / len(rewards), 1.0)
    
    rewards_str = ",".join(f"{r:.2f}" for r in rewards) if rewards else ""
    
    print(
        f"[END] success={str(success).lower()} steps={steps} score={total_score:.2f} rewards={rewards_str}",
        flush=True
    )

# -----------------------------
# LLM ACTION - MUST CALL PROXY
# -----------------------------
def get_llm_action(observation: Observation, step_num: int, task_id: str) -> Action:
    """Get action from LLM through the proxy"""
    
    if client is None:
        error_msg = "Client not initialized - cannot make LLM call"
        print(f"[ERROR] {error_msg}", flush=True)
        raise RuntimeError(error_msg)
    
    # Format observation for LLM
    logs_text = "\n".join(observation.logs[-5:])  # Last 5 logs
    metrics_text = ", ".join([f"{k}={v:.2f}" for k, v in observation.metrics.items()])
    alerts_text = ", ".join(observation.alerts) if observation.alerts else "None"
    
    prompt = f"""You are an SRE expert managing a production system.

Current System Status: {observation.system_status}
Task: {task_id}
Step: {step_num}/{observation.max_steps}

Recent Logs:
{logs_text}

Current Metrics:
{metrics_text}

Active Alerts:
{alerts_text}

Based on this information, choose ONE action to resolve the issue:
- restart_service (target: backend, frontend, or database)
- scale_service (target: api, worker, or backend)
- clear_cache (target: cache or redis)
- fix_db_connection (no target needed)
- noop (do nothing - only if system is healthy)

Return ONLY the action in this exact format: action_type target
Example: restart_service backend
Example: clear_cache cache
Example: fix_db_connection

Choose the most appropriate action:"""

    try:
        # Make API call through the proxy
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "You are an SRE expert. Return only the action and target, nothing else."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=30
        )
        
        # Parse response
        text = (response.choices[0].message.content or "").strip().lower()
        print(f"[INFO] LLM response: {text}", flush=True)
        
        # Parse action from response
        parts = text.split()
        
        if "restart" in text:
            action_type = "restart_service"
            target = parts[1] if len(parts) > 1 and parts[1] not in ["restart_service"] else "backend"
        elif "scale" in text:
            action_type = "scale_service"
            target = parts[1] if len(parts) > 1 else "api"
        elif "clear" in text or "cache" in text:
            action_type = "clear_cache"
            target = parts[1] if len(parts) > 1 else "cache"
        elif "fix_db" in text or "database" in text:
            action_type = "fix_db_connection"
            target = None
        elif "noop" in text:
            action_type = "noop"
            target = None
        else:
            # Default to restart if unclear
            action_type = "restart_service"
            target = "backend"
        
        # Create and return Action object
        return Action(action_type=action_type, target=target)
        
    except Exception as e:
        print(f"[ERROR] LLM call failed at step {step_num}: {e}", flush=True)
        raise RuntimeError(f"LLM API call failed: {e}")

# -----------------------------
# RUN SINGLE TASK
# -----------------------------
def run_task(task_id: str):
    """Run a single task episode"""
    log_start(task_id)
    
    # Create fresh environment
    env = SREEnvironment()
    
    rewards = []
    steps_taken = 0
    success = False
    last_error = None
    
    try:
        # Reset environment with task
        observation = env.reset(task_id=task_id)
        done = False
        
        # Get max steps for this task
        max_steps = observation.max_steps
        
        for step in range(1, max_steps + 1):
            if done:
                break
            
            # Get action from LLM (MUST go through proxy)
            try:
                action = get_llm_action(observation, step, task_id)
            except Exception as e:
                last_error = str(e)
                log_step(step, action if 'action' in locals() else {"error": "llm_failed"}, 0.0, True, error=last_error)
                break
            
            # Take step in environment
            try:
                observation, reward, done, info = env.step(action)
                
                # Extract reward value
                if hasattr(reward, 'value'):
                    reward_value = reward.value
                else:
                    reward_value = float(reward)
                
            except Exception as e:
                last_error = f"Environment step failed: {e}"
                log_step(step, action, 0.0, True, error=last_error)
                break
            
            rewards.append(reward_value)
            steps_taken = step
            
            log_step(step, action, reward_value, done)
            
            # Check for success (system healthy)
            if observation.system_status == "healthy":
                success = True
                break
        
        # If loop ended, check final status
        if not success and observation.system_status == "healthy":
            success = True
        
        # Get final score from info if available
        if 'info' in locals() and 'final_score' in info:
            final_score = info['final_score']
        else:
            final_score = sum(rewards) / len(rewards) if rewards else 0.0
        
    except Exception as e:
        last_error = f"Unexpected error: {e}"
        print(f"[ERROR] {last_error}", flush=True)
        import traceback
        traceback.print_exc()
        log_step(0, {"action_type": "error"}, 0.0, True, error=last_error)
    
    log_end(success, steps_taken, rewards)
    env.close()  # Clean up

# -----------------------------
# MAIN
# -----------------------------
def main():
    print("[INFO] Starting SRE Environment inference", flush=True)
    
    # Validate setup first
    if not validate_setup():
        print("[ERROR] Setup validation failed. Exiting.", flush=True)
        sys.exit(1)
    
    # Initialize client (proves we're using the proxy)
    if not init_client():
        print("[ERROR] Client initialization failed. Exiting.", flush=True)
        sys.exit(1)
    
    # Run all tasks
    tasks = ["easy_cache", "medium_db", "hard_outage"]
    
    for task in tasks:
        print(f"\n{'='*50}", flush=True)
        print(f"[INFO] Running task: {task}", flush=True)
        print(f"{'='*50}", flush=True)
        
        try:
            run_task(task)
        except Exception as e:
            print(f"[ERROR] Task {task} failed: {e}", flush=True)
            # Still try other tasks - don't crash completely
            import traceback
            traceback.print_exc()
        
        print(f"[INFO] Completed task: {task}\n", flush=True)
    
    print("[INFO] All tasks completed", flush=True)

if __name__ == "__main__":
    main()