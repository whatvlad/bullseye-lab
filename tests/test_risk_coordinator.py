from types import SimpleNamespace

from memebot.intelligence.risk.coordinator import RiskAssessmentCoordinator


def test_zero_assessment_limits_disable_local_quota():
    coordinator = RiskAssessmentCoordinator(
        None,
        None,
        None,
        None,  # type: ignore[arg-type]
        worker_count=1,
        queue_size=10,
        reassessment_interval_seconds=10,
        max_assessments_per_hour=0,
        max_assessments_per_day=0,
    )

    for index in range(5):
        event = SimpleNamespace(mint=f"mint-{index}")
        assert coordinator.enqueue(event)  # type: ignore[arg-type]

    assert coordinator._queue.qsize() == 5
