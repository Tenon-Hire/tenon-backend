import pytest
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

from app.domains.candidate_sessions import repository as cs_repo
from app.repositories.candidate_sessions import repository_basic as cs_basic_repo
from app.repositories.candidate_sessions import repository_tokens as cs_tokens_repo
from app.repositories.simulations.simulation import SIMULATION_STATUS_TERMINATED
from tests.factories import (
    create_candidate_session,
    create_recruiter,
    create_simulation,
)


def _compile_pg_sql(stmt) -> str:
    return str(
        stmt.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": True},
        )
    )


def test_get_by_id_for_update_locks_only_candidate_sessions():
    sql = _compile_pg_sql(cs_basic_repo._build_get_by_id_for_update_stmt(session_id=42))
    lower_sql = sql.lower()

    assert "for update" in lower_sql
    assert "for update of" in lower_sql
    assert "of candidate_sessions" in lower_sql
    assert "of simulations" not in lower_sql


def test_get_by_token_for_update_locks_only_candidate_sessions():
    sql = _compile_pg_sql(cs_tokens_repo._build_get_by_token_for_update_stmt("tok"))
    lower_sql = sql.lower()

    assert "for update" in lower_sql
    assert "for update of" in lower_sql
    assert "of candidate_sessions" in lower_sql
    assert "of simulations" not in lower_sql


@pytest.mark.asyncio
async def test_get_by_token_for_update(async_session):
    recruiter = await create_recruiter(async_session, email="tok@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)
    found_by_token = await cs_repo.get_by_token(async_session, cs.token)
    assert found_by_token is not None
    assert found_by_token.id == cs.id
    assert "simulation" not in inspect(found_by_token).unloaded

    found = await cs_repo.get_by_token_for_update(async_session, cs.token)
    assert found is not None
    assert found.id == cs.id
    assert "simulation" not in inspect(found).unloaded


@pytest.mark.asyncio
async def test_get_by_token_hides_terminated_simulations(async_session):
    recruiter = await create_recruiter(async_session, email="tok-term@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)
    sim.status = SIMULATION_STATUS_TERMINATED
    await async_session.commit()

    found_by_token = await cs_repo.get_by_token(async_session, cs.token)
    assert found_by_token is None

    found_for_update = await cs_repo.get_by_token_for_update(async_session, cs.token)
    assert found_for_update is None


@pytest.mark.asyncio
async def test_get_by_id_hides_terminated_simulations(async_session):
    recruiter = await create_recruiter(async_session, email="id-term@test.com")
    sim, _ = await create_simulation(async_session, created_by=recruiter)
    cs = await create_candidate_session(async_session, simulation=sim)
    sim.status = SIMULATION_STATUS_TERMINATED
    await async_session.commit()

    found_by_id = await cs_repo.get_by_id(async_session, cs.id)
    assert found_by_id is None

    found_for_update = await cs_repo.get_by_id_for_update(async_session, cs.id)
    assert found_for_update is None


@pytest.mark.asyncio
async def test_last_submission_helpers(async_session):
    assert await cs_repo.last_submission_at(async_session, 1) is None
    assert await cs_repo.last_submission_at_bulk(async_session, []) == {}
