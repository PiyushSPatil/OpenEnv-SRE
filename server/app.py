from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
from openai import OpenAI

from env.environment import SREEnvironment
from env.models import Action

# -----------------------------
# INIT APP
# -----------------------------
app = FastAPI(
    title="OpenEnv SRE Simulator",
    description="AI-powered DevOps/SRE simulation environment",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

env = SREEnvironment()

# -----------------------------
# LLM CLIENT FOR AGENT
# -----------------------------
api_key = os.environ["API_KEY"]
base_url = os.environ["API_BASE_URL"]
client = OpenAI(api_key=api_key, base_url=base_url)
model_name = "gpt-4o-mini"


# -----------------------------
# REQUEST MODELS
# -----------------------------
class ResetRequest(BaseModel):
    task_id: Optional[str] = "easy_cache"


class StepRequest(BaseModel):
    action_type: str
    target: Optional[str] = None


class AgentRunRequest(BaseModel):
    observation: dict


# -----------------------------
# ROOT
# -----------------------------
@app.get("/")
def root():
    return {
        "message": "OpenEnv SRE Simulator is running 🚀",
        "available_tasks": env.available_tasks()
    }


# -----------------------------
# RESET (CRITICAL FIX)
# -----------------------------
@app.post("/reset")
def reset(request: ResetRequest = Body(default=ResetRequest())):
    """
    Supports:
    ✔ POST with body
    ✔ POST without body (OpenEnv validator)
    """
    try:
        task_id = request.task_id if request else "easy_cache"

        observation = env.reset(task_id=task_id)

        return {
            "observation": observation.dict(),
            "done": False,
            "info": {}
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# STEP
# -----------------------------
@app.post("/step")
def step(request: StepRequest):
    try:
        action = Action(
            action_type=request.action_type,
            target=request.target
        )

        observation, reward, done, info = env.step(action)

        return {
            "observation": observation.dict(),
            "reward": reward.dict(),
            "done": done,
            "info": info
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# AGENT RUN
# -----------------------------
@app.post("/agent/run")
def agent_run(request: AgentRunRequest):
    try:
        obs = request.observation

        prompt = f"""
You are an expert Site Reliability Engineer (SRE).

Fix the system and make it healthy.

Logs: {obs.get('logs')}
Metrics: {obs.get('metrics')}
Alerts: {obs.get('alerts')}

Rules:
- Database error → fix_db_connection
- CPU > 80 → scale_service
- Latency > 180 → clear_cache
- Otherwise → restart_service

Respond ONLY with:
clear_cache, fix_db_connection, scale_service, restart_service
"""

        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": "You are an SRE expert."},
                {"role": "user", "content": prompt},
            ],
            temperature=0,
        )

        text = (response.choices[0].message.content or "").strip().lower()

        if "fix_db_connection" in text:
            action = {"action_type": "fix_db_connection", "target": None}
        elif "scale_service" in text:
            action = {"action_type": "scale_service", "target": "api"}
        elif "clear_cache" in text:
            action = {"action_type": "clear_cache", "target": None}
        else:
            action = {"action_type": "restart_service", "target": "backend"}

        return {"action": action}

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# STATE
# -----------------------------
@app.get("/state")
def state():
    try:
        return env.state()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# HEALTH
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}


# -----------------------------
# ENTRY POINT (CRITICAL FOR VALIDATOR)
# -----------------------------
def main():
    """
    Required for OpenEnv validator:
    server = "server.app:main"
    """
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()