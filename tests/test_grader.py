from env.grader import SREGrader
from env.models import InternalState


def test_grader():
    grader = SREGrader()

    state = InternalState(
        db_connected=True,
        cache_clean=True,
        services_running={"backend": True},
        cpu_usage=50,
        latency=100,
        issue_identified=True,
        issue_fixed=True,
        step_count=3,
        max_steps=6,
        task_id="easy_cache",
    )

    score = grader.grade(state)

    assert 0.0 <= score <= 1.0