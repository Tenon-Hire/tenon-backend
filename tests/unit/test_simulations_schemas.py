from app.domains.simulations.schemas import SimulationDetailTask


def test_simulation_detail_task_serializes_optional_fields():
    task = SimulationDetailTask(
        dayIndex=1,
        title="Task",
        type="code",
        description=None,
        rubric=None,
        maxScore=10,
        preProvisioned=True,
        templateRepoFullName="org/repo",
    )

    serialized = task.model_dump()
    assert serialized["maxScore"] == 10
    assert serialized["preProvisioned"] is True
    assert serialized["templateRepoFullName"] == "org/repo"
