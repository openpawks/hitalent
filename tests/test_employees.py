import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_employee(client: AsyncClient):
    dept = await client.post(
        "/departments",
        json={"name": "Engineering", "parent_id": None},
    )
    dept_id = dept.json()["id"]

    res = await client.post(
        f"/departments/{dept_id}/employees",
        json={
            "full_name": "John Doe",
            "position": "Backend Engineer",
            "hired_at": None,
        },
    )

    assert res.status_code == 201

    data = res.json()
    assert data["full_name"] == "John Doe"
    assert data["position"] == "Backend Engineer"
    assert isinstance(data["id"], int)


@pytest.mark.asyncio
async def test_create_employee_invalid_department(client: AsyncClient):
    res = await client.post(
        "/departments/99999/employees",
        json={
            "full_name": "John Doe",
            "position": "Backend Engineer",
            "hired_at": None,
        },
    )

    assert res.status_code == 404
    assert res.json()["detail"] == "Department not found"
