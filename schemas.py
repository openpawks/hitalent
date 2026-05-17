from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class DepartmentBase(BaseModel):
    name: str
    parent_id: int | None = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentResponse(DepartmentBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DepartmentUpdatePartial(BaseModel):
    name: str | None = None
    parent_id: int | None = None


class EmployeeBase(BaseModel):
    full_name: str
    position: str
    hired_at: datetime | None = None


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeResponse(EmployeeBase):
    id: int
    department_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DepartmentTree(BaseModel):
    department: DepartmentResponse
    employees: list[EmployeeResponse] | None = None
    children: list["DepartmentTree"] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


DepartmentTree.model_rebuild()
