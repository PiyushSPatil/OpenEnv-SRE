from env.environment import SREEnvironment
from env.models import Action


def test_reset():
    env = SREEnvironment()
    obs = env.reset("easy_cache")
    assert obs is not None


def test_step():
    env = SREEnvironment()
    env.reset("easy_cache")

    action = Action(action_type="clear_cache")
    obs, reward, done, _ = env.step(action)

    assert reward.value is not None