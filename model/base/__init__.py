from .sqlmodel_base import SQLModelBase
from .table_base import TableBase, UUIDTableBase

# 新的 Mixin 类（从 foxline 项目移植）
from ..mixin.table import (
    TableBaseMixin,
    UUIDTableBaseMixin,
    ListResponse,
    TableViewRequest,
    TimeFilterRequest,
    PaginationRequest,
)

# 保持向后兼容：TableBase/UUIDTableBase 作为旧名称继续可用
# 新代码推荐使用 TableBaseMixin/UUIDTableBaseMixin

__all__ = [
    "SQLModelBase",
    "TableBase",
    "UUIDTableBase",
    # 新的 Mixin 类
    "TableBaseMixin",
    "UUIDTableBaseMixin",
    "ListResponse",
    "TableViewRequest",
    "TimeFilterRequest",
    "PaginationRequest",
]
