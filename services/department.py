import models

from schemas import (
    DepartmentCreate,
    DepartmentResponse,
    DepartmentUpdatePartial,
    EmployeeCreate,
    EmployeeResponse,
    DepartmentTree,
)

from sqlalchemy import select, delete, update, literal

from sqlalchemy.ext.asyncio import AsyncSession

from typing import Literal

from collections import defaultdict

from .exceptions import (
    DepartmentAlreadyExistsError,
    ParentDepartmentNotFoundError,
    DepartmentNotFoundError,
    InvalidReassignError,
    EmployeeAlreadyExistsError,
    InvalidDepartmentHierarchyError,
)

from config import settings

Mode = Literal["cascade", "reassign"]


class DepartmentService:
    MAX_TREE_DEPTH = settings.max_tree_depth

    @staticmethod
    async def create_department(department: DepartmentCreate, db: AsyncSession):
        result = await db.execute(
            select(models.Department).where(models.Department.name == department.name)
        )
        existing_department = result.scalars().first()

        if existing_department:
            raise DepartmentAlreadyExistsError()

        result = await db.execute(
            select(models.Department).where(
                models.Department.id == department.parent_id
            )
        )
        parent_department = result.scalars().first()
        if department.parent_id and not parent_department:
            raise ParentDepartmentNotFoundError()

        new_department = models.Department(**department.model_dump())
        db.add(new_department)
        await db.commit()
        await db.refresh(new_department)
        return new_department

    @staticmethod
    async def get_department(
        id: int,
        db: AsyncSession,
        depth: int = 1,
        include_employees: bool = True,
    ) -> DepartmentTree:
        depth = max(0, min(depth, DepartmentService.MAX_TREE_DEPTH))

        department_ids = await DepartmentService._get_subtree_department_ids(
            department_id=id, depth=depth, db=db
        )

        if not department_ids:
            raise DepartmentNotFoundError()

        result = await db.execute(
            select(models.Department).where(models.Department.id.in_(department_ids))
        )

        departments = result.scalars().all()

        employees_by_department = defaultdict(list)

        if include_employees:
            result = await db.execute(
                select(models.Employee).where(
                    models.Employee.department_id.in_(department_ids)
                )
            )

            employees = result.scalars().all()

            for employee in employees:
                employees_by_department[employee.department_id].append(
                    EmployeeResponse.model_validate(employee)
                )

        return DepartmentService._build_department_tree(
            root_department_id=id,
            departments=departments,
            employees_by_department=employees_by_department,
        )

    @staticmethod
    async def _get_subtree_department_ids(
        department_id: int,
        depth: int,
        db: AsyncSession,
    ) -> list[int]:

        cte = (
            select(
                models.Department.id,
                literal(0).label("level"),
            )
            .where(models.Department.id == department_id)
            .cte(name="department_tree", recursive=True)
        )

        children_cte = (
            select(
                models.Department.id,
                (cte.c.level + 1).label("level"),
            )
            .where(models.Department.parent_id == cte.c.id)
            .where(cte.c.level < depth)
        )

        cte = cte.union_all(children_cte)

        result = await db.execute(select(cte.c.id))

        return result.scalars().all()

    @staticmethod
    def _build_department_tree(
        root_department_id: int,
        departments: list[models.Department],
        employees_by_department: dict[int, list[EmployeeResponse]],
    ) -> DepartmentTree:

        nodes: dict[int, DepartmentTree] = {}

        for department in departments:
            nodes[department.id] = DepartmentTree(
                department=DepartmentResponse.model_validate(department),
                employees=employees_by_department.get(department.id, []),
            )

        root = None

        for department in departments:
            current_node = nodes[department.id]

            if department.id == root_department_id:
                root = current_node

            if department.parent_id is not None:
                parent_node = nodes.get(department.parent_id)

                if parent_node:
                    parent_node.children.append(current_node)

        return root

    @staticmethod
    async def update_department_partial(
        id: int,
        department_data: DepartmentUpdatePartial,
        db: AsyncSession,
    ) -> DepartmentResponse:
        result = await db.execute(
            select(models.Department).where(models.Department.id == id)
        )
        department = result.scalars().first()

        if not department:
            raise DepartmentNotFoundError()

        if department_data.parent_id == department.id:
            raise InvalidDepartmentHierarchyError()

        if (
            department_data.parent_id is not None
            and department_data.parent_id != department.id
        ):
            result = await db.execute(
                select(models.Department).where(
                    models.Department.id == department_data.parent_id
                )
            )

            parent_department = result.scalars().first()

            if not parent_department:
                raise ParentDepartmentNotFoundError()

        update_data = department_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(department, field, value)

        await db.commit()
        await db.refresh(department)
        return department

    @staticmethod
    async def delete_department(
        id: int,
        db: AsyncSession,
        mode: Mode,
        reassign_to_department_id: int | None = None,
    ) -> None:
        result = await db.execute(
            select(models.Department).where(models.Department.id == id)
        )

        department = result.scalars().first()

        if not department:
            raise DepartmentNotFoundError()

        match mode:
            case "cascade":
                await DepartmentService._cascade_delete(
                    department_id=id,
                    db=db,
                )
            case "reassign":
                if reassign_to_department_id is None:
                    raise InvalidReassignError()

                await DepartmentService._reassign_delete(
                    department=department,
                    reassign_to_department_id=reassign_to_department_id,
                    db=db,
                )

        await db.commit()

    @staticmethod
    async def _cascade_delete(
        department_id: int,
        db: AsyncSession,
    ) -> None:
        cte = (
            select(models.Department.id)
            .where(models.Department.id == department_id)
            .cte(name="subdeps", recursive=True)
        )

        cte = cte.union_all(
            select(models.Department.id).where(models.Department.parent_id == cte.c.id)
        )

        result = await db.execute(select(cte.c.id))

        department_ids = result.scalars().all()

        await db.execute(
            delete(models.Employee).where(
                models.Employee.department_id.in_(department_ids)
            )
        )

        await db.execute(
            delete(models.Department).where(models.Department.id.in_(department_ids))
        )

    @staticmethod
    async def _reassign_delete(
        department: models.Department,
        reassign_to_department_id: int,
        db: AsyncSession,
    ) -> None:
        await db.execute(
            update(models.Employee)
            .where(models.Employee.department_id == department.id)
            .values(department_id=reassign_to_department_id)
        )

        await db.delete(department)

    @staticmethod
    async def create_employee(
        id: int,
        employee: EmployeeCreate,
        db: AsyncSession,
    ) -> EmployeeResponse:
        result = await db.execute(
            select(models.Employee).where(
                models.Employee.full_name == employee.full_name
            )
        )
        existing_employee = result.scalars().first()

        if existing_employee:
            raise EmployeeAlreadyExistsError()

        result = await db.execute(
            select(models.Department).where(models.Department.id == id)
        )
        department = result.scalars().first()

        if not department:
            raise DepartmentNotFoundError()

        new_employee = models.Employee(department_id=id, **employee.model_dump())
        db.add(new_employee)
        await db.commit()
        await db.refresh(new_employee)
        return new_employee
