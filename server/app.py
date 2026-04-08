from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any

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

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allow frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

env = SREEnvironment()


# -----------------------------
# REQUEST MODELS
# -----------------------------
class ResetRequest(BaseModel):
    task_id: Optional[str] = "easy_cache"


class StepRequest(BaseModel):
    action_type: str
    target: Optional[str] = None


# -----------------------------
# ROOT (optional)
# -----------------------------
@app.get("/")
def root():
    return {
        "message": "OpenEnv SRE Simulator is running 🚀",
        "available_tasks": env.available_tasks()
    }


# -----------------------------
# RESET ENDPOINT
# -----------------------------
@app.post("/reset")
def reset(request: ResetRequest):
    try:
        observation = env.reset(task_id=request.task_id)
        return {
            "observation": observation.dict(),
            "done": False,
            "info": {}
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# STEP ENDPOINT
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
# STATE ENDPOINT
# -----------------------------
@app.get("/state")
def state():
    try:
        return env.state()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# HEALTH CHECK (VERY IMPORTANT)
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}