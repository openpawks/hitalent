class DepartmentAlreadyExistsError(Exception):
    pass


class ParentDepartmentNotFoundError(Exception):
    pass


class DepartmentNotFoundError(Exception):
    pass


class InvalidReassignError(Exception):
    pass


class EmployeeAlreadyExistsError(Exception):
    pass


class InvalidDepartmentHierarchyError(Exception):
    pass
