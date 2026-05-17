import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_department(client: AsyncClient):
    res = await client.post(
        "/departments",
        json={"name": "Engineering", "parent_id": None},
    )

    assert res.status_code == 201
    data = res.json()

    assert data["name"] == "Engineering"
    assert isinstance(data["id"], int)


@pytest.mark.asyncio
async def test_duplicate_department_name(client: AsyncClient):
    payload = {"name": "Engineering", "parent_id": None}

    await client.post("/departments", json=payload)
    res = await client.post("/departments", json=payload)

    assert res.status_code == 400


@pytest.mark.asyncio
async def test_invalid_parent_department(client: AsyncClient):
    res = await client.post(
        "/departments",
        json={"name": "Backend", "parent_id": 99999},
    )

    assert res.status_code == 404


@pytest.mark.asyncio
async def test_department_tree(client: AsyncClient):
    root = await client.post(
        "/departments",
        json={"name": "Engineering", "parent_id": None},
    )
    root_id = root.json()["id"]

    await client.post(
        "/departments",
        json={"name": "Backend", "parent_id": root_id},
    )

    res = await client.get(f"/departments/{root_id}")

    assert res.status_code == 200
    data = res.json()

    assert data["department"]["name"] == "Engineering"
    assert len(data["children"]) == 1


@pytest.mark.asyncio
async def test_self_parenting_not_allowed(client: AsyncClient):
    res1 = await client.post(
        "/departments",
        json={"name": "Engineering", "parent_id": None},
    )
    dep_id = res1.json()["id"]

    res2 = await client.patch(
        f"/departments/{dep_id}",
        json={"parent_id": dep_id},
    )

    assert res2.status_code == 422


@pytest.mark.asyncio
async def test_cascade_delete(client: AsyncClient):
    root = await client.post(
        "/departments",
        json={"name": "Engineering", "parent_id": None},
    )
    root_id = root.json()["id"]

    child = await client.post(
        "/departments",
        json={"name": "Backend", "parent_id": root_id},
    )
    child_id = child.json()["id"]

    res = await client.delete(f"/departments/{root_id}?mode=cascade")
    assert res.status_code == 204

    assert (await client.get(f"/departments/{root_id}")).status_code == 404
    assert (await client.get(f"/departments/{child_id}")).status_code == 404


@pytest.mark.asyncio
async def test_reassign_requires_target(client: AsyncClient):
    dep = await client.post(
        "/departments",
        json={"name": "Engineering", "parent_id": None},
    )

    res = await client.delete(f"/departments/{dep.json()['id']}?mode=reassign")

    assert res.status_code == 422


@pytest.mark.asyncio
async def test_reassign_delete(client: AsyncClient):
    eng = await client.post(
        "/departments",
        json={"name": "Engineering", "parent_id": None},
    )
    eng_id = eng.json()["id"]

    platform = await client.post(
        "/departments",
        json={"name": "Platform", "parent_id": None},
    )
    platform_id = platform.json()["id"]

    await client.post(
        f"/departments/{eng_id}/employees",
        json={
            "full_name": "John Doe",
            "position": "Backend Engineer",
            "hired_at": None,
        },
    )

    res = await client.delete(
        f"/departments/{eng_id}?mode=reassign&reassign_to_department_id={platform_id}"
    )
    assert res.status_code == 204

    # Get the platform department with employees
    tree = await client.get(f"/departments/{platform_id}?include_employees=true")
    assert tree.status_code == 200

    data = tree.json()

    # Recursively search for John Doe in department tree
    def find_employee(node, name):
        employees = node.get("employees") or []
        for emp in employees:
            if emp.get("full_name") == name:
                return True
        for child in node.get("children", []):
            if find_employee(child, name):
                return True
        return False

    assert find_employee(data, "John Doe"), (
        "John Doe should be reassigned to Platform department"
    )
