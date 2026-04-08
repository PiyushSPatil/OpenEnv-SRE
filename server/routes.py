from fastapi import APIRouter, HTTPException

from env.environment import SREEnvironment
from env.models import Action
from .schemas import ResetRequest, StepRequest

router = APIRouter()
env = SREEnvironment()


@router.post("/reset")
def reset(request: ResetRequest):
    try:
        obs = env.reset(task_id=request.task_id)
        return {"observation": obs.dict(), "done": False, "info": {}}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/step")
def step(request: StepRequest):
    try:
        action = Action(action_type=request.action_type, target=request.target)
        obs, reward, done, info = env.step(action)

        return {
            "observation": obs.dict(),
            "reward": reward.dict(),
            "done": done,
            "info": info,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/state")
def state():
    return env.state()