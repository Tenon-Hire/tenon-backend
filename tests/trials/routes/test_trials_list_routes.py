import pytest


@pytest.mark.asyncio
async def test_list_trials_empty(authed_client):
    resp = await authed_client.get("/api/trials")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_list_trials_returns_two(authed_client):
    payload1 = {
        "title": "Sim A",
        "role": "Backend Engineer",
        "techStack": "Node.js, PostgreSQL",
        "seniority": "Mid",
        "focus": "A",
    }
    payload2 = {
        "title": "Sim B",
        "role": "Backend Engineer",
        "techStack": "Node.js, PostgreSQL",
        "seniority": "Mid",
        "focus": "B",
    }
    r1 = await authed_client.post("/api/trials", json=payload1)
    r2 = await authed_client.post("/api/trials", json=payload2)
    assert r1.status_code == 201 and r2.status_code == 201

    resp = await authed_client.get("/api/trials")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    titles = {x["title"] for x in data}
    assert titles == {"Sim A", "Sim B"}
    for item in data:
        assert "id" in item
        assert item["role"] == "Backend Engineer"
        assert item["techStack"] == "Node.js, PostgreSQL"
        assert "createdAt" in item
        assert item["numCandidates"] == 0
