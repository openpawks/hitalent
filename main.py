from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, status

from schemas import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdatePartial,
    EmployeeCreate,
    EmployeeResponse,
    DepartmentTree,
)

from db import get_db, async_engine

from sqlalchemy.ext.asyncio import AsyncSession

from typing import Literal, Annotated

from services.department import DepartmentService

from services.exceptions import (
    DepartmentAlreadyExistsError,
    ParentDepartmentNotFoundError,
    DepartmentNotFoundError,
    InvalidReassignError,
    EmployeeAlreadyExistsError,
    InvalidDepartmentHierarchyError,
)

Mode = Literal["cascade", "reassign"]


@asynccontextmanager
async def lifespan(_app: FastAPI):

    yield
    await async_engine.dispose()


app = FastAPI(lifespan=lifespan)


@app.post(
    "/departments",
    response_model=DepartmentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_department(
    department: DepartmentCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        result = await DepartmentService.create_department(department, db)

        return result
    except DepartmentAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department already exists",
        )
    except ParentDepartmentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent department not found",
        )


@app.get("/departments/{id}", response_model=DepartmentTree)
async def get_department(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    depth: int = 1,
    include_employees: bool = True,
):
    try:
        result = await DepartmentService.get_department(
            id, db, depth, include_employees
        )

        return result
    except DepartmentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found",
        )


@app.patch("/departments/{id}", response_model=DepartmentResponse)
async def update_department_partial(
    id: int,
    department_data: DepartmentUpdatePartial,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        result = await DepartmentService.update_department_partial(
            id, department_data, db
        )

        return result
    except DepartmentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
        )
    except InvalidDepartmentHierarchyError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Self-parenting is not allowed",
        )
    except ParentDepartmentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent department not found",
        )


@app.delete("/departments/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_department(
    id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
    mode: Mode,  # cascade or reassign
    reassign_to_department_id: int | None = None,
):
    try:
        result = await DepartmentService.delete_department(
            id, db, mode, reassign_to_department_id
        )
        return result
    except DepartmentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
        )
    except InvalidReassignError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="reassign_to_department_id is required when mode='reassign'",
        )


@app.post(
    "/departments/{id}/employees",
    response_model=EmployeeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_employee(
    id: int,
    employee: EmployeeCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    try:
        result = await DepartmentService.create_employee(id, employee, db)
        return result
    except EmployeeAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee already exists",
        )
    except DepartmentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Department not found"
        )
