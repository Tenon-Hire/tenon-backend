import pytest


@pytest.mark.asyncio
async def test_list_trials_includes_seniority_and_ai_eval_summary(authed_client):
    payload = {
        "title": "Sim With AI Settings",
        "role": "Frontend Engineer",
        "techStack": "react-nextjs",
        "seniority": "mid",
        "focus": "Prioritize API ergonomics.",
        "companyContext": {"domain": "social", "productArea": "creator tools"},
        "ai": {
            "noticeVersion": "mvp1",
            "evalEnabledByDay": {
                "1": True,
                "2": True,
                "3": False,
                "4": False,
                "5": True,
            },
        },
    }
    create_res = await authed_client.post("/api/trials", json=payload)
    assert create_res.status_code == 201, create_res.text
    sim_id = create_res.json()["id"]

    list_res = await authed_client.get("/api/trials")
    assert list_res.status_code == 200, list_res.text
    item = next(x for x in list_res.json() if x["id"] == sim_id)
    assert item["seniority"] == "mid"
    assert item["companyContext"] == payload["companyContext"]
    assert item["ai"]["noticeVersion"] == "mvp1"
    assert item["ai"]["evalEnabledByDay"] == payload["ai"]["evalEnabledByDay"]
