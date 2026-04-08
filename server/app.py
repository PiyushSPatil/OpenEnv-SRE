from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

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
# REQUEST MODELS
# -----------------------------
class ResetRequest(BaseModel):
    task_id: Optional[str] = "easy_cache"


class StepRequest(BaseModel):
    action_type: str
    target: Optional[str] = None


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