#!/usr/bin/env python3
import os
import sys
import json
import traceback
from openai import OpenAI

# Import your environment DIRECTLY (no HTTP)
try:
    from env.environment import SREEnvironment
    from env.models import Action
except ImportError:
    try:
        from environment import SREEnvironment
        from models import Action
    except ImportError as e:
        print(f"[ERROR] Cannot import environment: {e}", flush=True)
        sys.exit(1)

# -----------------------------
# CONFIGURATION
# -----------------------------
HF_TOKEN = os.getenv("HF_TOKEN")
API_BASE_URL = os.getenv("API_BASE_URL")
MODEL_NAME = os.getenv("MODEL_NAME") or "Qwen/Qwen2.5-72B-Instruct"

MAX_STEPS = 10
ENV_NAME = "openenv_sre"

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
        client.models.list()
        print("[INFO] OpenAI client initialized successfully", flush=True)
        return True
    except Exception as e:
        print(f"[ERROR] Client init failed: {e}", flush=True)
        return False

# -----------------------------
# LOGGING
# -----------------------------
def log_start(task):
    print(f"[START] task={task} env={ENV_NAME} model={MODEL_NAME}", flush=True)

def log_step(step, action, reward, done, error=None):
    error_str = error if error else "null"
    if hasattr(action, 'action_type'):
        action_str = json.dumps({"action_type": action.action_type, "target": action.target})
    else:
        action_str = json.dumps(action)
    
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
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.2f} rewards={rewards_str}", flush=True)

# -----------------------------
# LLM ACTION
# -----------------------------
def get_llm_action(observation, step_num: int, task_id: str):
    """Get action from LLM through proxy"""
    
    if client is None:
        raise RuntimeError("OpenAI client not initialized")
    
    # Extract observation data
    logs_text = "\n".join(observation.logs[-5:]) if observation.logs else "No logs"
    metrics_text = ", ".join([f"{k}={v}" for k, v in observation.metrics.items()])
    alerts_text = ", ".join(observation.alerts) if observation.alerts else "None"
    
    prompt = f"""You are an SRE expert.

Status: {observation.system_status}
Task: {task_id}
Step: {step_num}/{observation.max_steps}

Logs: {logs_text}
Metrics: {metrics_text}
Alerts: {alerts_text}

Choose: restart_service, scale_service, clear_cache, fix_db_connection, noop
Return JSON: {{"action_type": "...", "target": "..."}}"""

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": "Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            max_tokens=50
        )
        
        text = response.choices[0].message.content
        print(f"[INFO] LLM response: {text}", flush=True)
        
        # Parse JSON
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        action_data = json.loads(text.strip())
        
        # Create Action object
        return Action(
            action_type=action_data.get("action_type", "restart_service"),
            target=action_data.get("target")
        )
        
    except Exception as e:
        print(f"[ERROR] LLM call failed: {e}", flush=True)
        raise

# -----------------------------
# RUN TASK
# -----------------------------
def run_task(task_id: str):
    log_start(task_id)
    
    env = SREEnvironment()
    rewards = []
    steps_taken = 0
    success = False
    info = {}
    
    try:
        observation = env.reset(task_id=task_id)
        done = False
        
        for step in range(1, observation.max_steps + 1):
            if done:
                break
            
            action = get_llm_action(observation, step, task_id)
            observation, reward, done, info = env.step(action)
            
            reward_value = reward.value if hasattr(reward, 'value') else float(reward)
            rewards.append(reward_value)
            steps_taken = step
            
            log_step(step, action, reward_value, done)
            
            if observation.system_status == "healthy":
                success = True
                break
        
        final_score = info.get('final_score', sum(rewards) / len(rewards) if rewards else 0.0)
        
    except Exception as e:
        print(f"[ERROR] Task failed: {e}", flush=True)
        traceback.print_exc()
        final_score = 0.0
    
    log_end(success, steps_taken, rewards, final_score)
    env.close()

# -----------------------------
# MAIN
# -----------------------------
def main():
    print("[INFO] Starting inference script", flush=True)
    
    if not HF_TOKEN or not API_BASE_URL:
        print("[ERROR] Missing HF_TOKEN or API_BASE_URL", flush=True)
        sys.exit(1)
    
    if not init_client():
        sys.exit(1)
    
    for task in ["easy_cache", "medium_db", "hard_outage"]:
        print(f"\n{'='*50}\n[INFO] Running task: {task}\n{'='*50}", flush=True)
        run_task(task)
    
    print("[INFO] All tasks completed", flush=True)
    sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[FATAL] {e}", flush=True)
        traceback.print_exc()
        sys.exit(1)